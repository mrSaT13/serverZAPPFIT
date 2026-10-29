<!-- Training inventory manager: the dumbbells/barbells/machines the user owns
with weights — the AI plan generator filters its catalog to these. -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { LoaderCircle, Plus, Trash2 } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { inputFieldClass } from '@/components/ui/input/fieldClasses'
import { useToasts } from '@/composables/useToasts'
import { toNumberOrNull } from '@/utils/number'
import { fetchCatalogMeta, type CatalogMeta } from '@/features/strength/services/workouts'
import {
  useCreateEquipmentMutation,
  useDeleteEquipmentMutation,
  useEquipmentQuery,
} from '@/features/gears/composables/useEquipment'

const open = defineModel<boolean>('open', { required: true })

const { t } = useI18n()
const toasts = useToasts()

const itemsQuery = useEquipmentQuery()
const createMutation = useCreateEquipmentMutation()
const deleteMutation = useDeleteEquipmentMutation()

const items = computed(() => itemsQuery.data.value ?? [])
const isLoading = computed(() => itemsQuery.isPending.value)

/** Catalog equipment dictionary for the type select (Barbell, Dumbbell, …). */
const meta = ref<CatalogMeta | null>(null)
async function ensureMeta(): Promise<void> {
  if (meta.value) return
  try {
    meta.value = await fetchCatalogMeta()
  } catch {
    /* select degrades to the free-text name only */
  }
}
void ensureMeta()

/** Translated label for a catalog equipment entry (English fallback). */
function equipmentLabel(name: string): string {
  const key = `workouts.catalog.equipment.${name}`
  const label = t(key)
  return label === key ? name : label
}

// ---- add form ----
const name = ref('')
const equipmentId = ref('')
const weightKg = ref('')
const quantity = ref('1')

const canSubmit = computed(() => name.value.trim().length > 0)

async function submit(): Promise<void> {
  try {
    await createMutation.mutateAsync({
      name: name.value.trim(),
      equipment_id: equipmentId.value !== '' ? Number(equipmentId.value) : null,
      weight_kg: toNumberOrNull(weightKg.value),
      quantity: toNumberOrNull(quantity.value) ?? 1,
    })
    name.value = ''
    equipmentId.value = ''
    weightKg.value = ''
    quantity.value = '1'
    toasts.success(t('gears.equipment.added'))
  } catch {
    toasts.error(t('gears.equipment.addError'))
  }
}

async function remove(id: number): Promise<void> {
  try {
    await deleteMutation.mutateAsync(id)
    toasts.success(t('gears.equipment.removed'))
  } catch {
    toasts.error(t('gears.equipment.removeError'))
  }
}

/** "Гантели (10 кг) x2" style line for the list. */
function describe(item: {
  name: string
  weight_kg: string | number | null
  quantity: number
}): string {
  const parts: string[] = []
  if (item.weight_kg != null) parts.push(`${item.weight_kg} kg`)
  if (item.quantity > 1) parts.push(`x${item.quantity}`)
  return parts.length > 0 ? `${item.name} (${parts.join(', ')})` : item.name
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-lg" :close-label="t('gears.equipment.close')">
      <DialogHeader>
        <DialogTitle>{{ t('gears.equipment.title') }}</DialogTitle>
        <DialogDescription>{{ t('gears.equipment.subtitle') }}</DialogDescription>
      </DialogHeader>

      <form class="mt-2 flex flex-col gap-3" novalidate @submit.prevent="submit">
        <div class="grid grid-cols-[1fr_7rem_6rem] items-end gap-2">
          <FormField :label="t('gears.equipment.nameLabel')">
            <template #default="{ fieldId }">
              <Input
                :id="fieldId"
                v-model="name"
                :class="inputFieldClass"
                :placeholder="t('gears.equipment.namePlaceholder')"
                maxlength="100"
                required
              />
            </template>
          </FormField>
          <FormField :label="t('gears.equipment.weightLabel')">
            <template #default="{ fieldId }">
              <Input
                :id="fieldId"
                v-model="weightKg"
                :class="inputFieldClass"
                type="number"
                inputmode="decimal"
                step="0.01"
                min="0"
                placeholder="10"
              />
            </template>
          </FormField>
          <FormField :label="t('gears.equipment.quantityLabel')">
            <template #default="{ fieldId }">
              <Input
                :id="fieldId"
                v-model="quantity"
                :class="inputFieldClass"
                type="number"
                inputmode="numeric"
                min="1"
                max="999"
              />
            </template>
          </FormField>
        </div>

        <FormField v-if="meta" :label="t('gears.equipment.typeLabel')">
          <template #default="{ fieldId }">
            <Select :id="fieldId" v-model="equipmentId">
              <option value="">{{ t('gears.equipment.typeAny') }}</option>
              <option v-for="e in meta.equipment" :key="e.id" :value="String(e.id)">
                {{ equipmentLabel(e.name) }}
              </option>
            </Select>
          </template>
        </FormField>

        <Button
          type="submit"
          class="w-full"
          :disabled="!canSubmit || createMutation.isPending.value"
        >
          <LoaderCircle
            v-if="createMutation.isPending.value"
            class="size-4 animate-spin"
            aria-hidden="true"
          />
          <Plus v-else class="size-4" aria-hidden="true" />
          {{ t('gears.equipment.add') }}
        </Button>
      </form>

      <div class="flex flex-col gap-2">
        <p class="text-caption">{{ t('gears.equipment.listTitle') }}</p>
        <div v-if="isLoading" class="text-hint">{{ t('gears.equipment.loading') }}</div>
        <div v-else-if="items.length === 0" class="text-hint">
          {{ t('gears.equipment.empty') }}
        </div>
        <ul v-else class="flex max-h-64 flex-col gap-1 overflow-auto">
          <li
            v-for="item in items"
            :key="item.id"
            class="flex items-center gap-2 rounded-input border px-3 py-2"
          >
            <span class="min-w-0 flex-1 truncate text-body">{{ describe(item) }}</span>
            <Button
              size="sm"
              variant="ghost"
              class="text-destructive"
              :aria-label="t('gears.equipment.remove')"
              :disabled="deleteMutation.isPending.value"
              @click="remove(item.id)"
            >
              <Trash2 class="size-4" aria-hidden="true" />
            </Button>
          </li>
        </ul>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="open = false">{{ t('gears.equipment.close') }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
