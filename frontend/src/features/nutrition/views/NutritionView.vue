<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, Plus, Trash2, Utensils, ScanLine } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useToasts } from '@/composables/useToasts'
import NutritionScannerDialog from '@/features/nutrition/components/NutritionScannerDialog.vue'
import { fetchLogs, createLog, deleteLog, searchOff, getOffProduct, fetchSummary, type MealLog, type OffProduct } from '@/features/nutrition/services/nutrition'

const { t } = useI18n()
const toasts = useToasts()

const today = new Date().toISOString().slice(0,10)
const selectedDate = ref(today)
const logs = ref<MealLog[]>([])
const offQuery = ref('')
const offResults = ref<OffProduct[]>([])
const summary = ref<{ intake_calories: number; intake_protein: number; intake_carbs: number; intake_fat: number; burned_calories: number | null; net_calories: number | null } | null>(null)

const form = ref({ meal_type: 'breakfast' as MealLog['meal_type'], product_name: '', calories: '' as string, protein: '', carbs: '', fat: '', portion_g: '100', off_barcode: '' })
const scannerOpen = ref(false)

async function load() {
  logs.value = await fetchLogs(selectedDate.value)
  try { summary.value = await fetchSummary(selectedDate.value) } catch { summary.value = null }
}
async function onScanned(code: string) {
  try {
    const p = await getOffProduct(code.trim())
    fillFromOff(p)
  } catch { toasts.error('Продукт не найден') }
}
async function doSearch() {
  if (offQuery.value.trim().length < 2) return
  offResults.value = await searchOff(offQuery.value.trim())
}
function fillFromOff(p: OffProduct) {
  form.value.product_name = p.product_name ?? ''
  form.value.off_barcode = p.barcode ?? ''
  const portion = Number(form.value.portion_g || '100')
  const factor = portion / 100
  if (p.calories_100g != null) form.value.calories = String(Math.round(p.calories_100g * factor))
  if (p.proteins_100g != null) form.value.protein = String((p.proteins_100g * factor).toFixed(1))
  if (p.carbs_100g != null) form.value.carbs = String((p.carbs_100g * factor).toFixed(1))
  if (p.fat_100g != null) form.value.fat = String((p.fat_100g * factor).toFixed(1))
  toasts.success('Заполнено из OFF')
}
async function onScanBarcode() {
  scannerOpen.value = true
}
async function onManualBarcode() {
  const code = prompt('Введи штрих-код вручную:')
  if (!code) return
  await onScanned(code)
}
async function add() {
  if (!form.value.product_name.trim()) { toasts.error('Укажи продукт'); return }
  await createLog({
    date: selectedDate.value,
    meal_type: form.value.meal_type,
    product_name: form.value.product_name.trim(),
    calories: form.value.calories ? Number(form.value.calories) : null,
    protein: form.value.protein ? Number(form.value.protein) : null,
    carbs: form.value.carbs ? Number(form.value.carbs) : null,
    fat: form.value.fat ? Number(form.value.fat) : null,
    portion_g: form.value.portion_g ? Number(form.value.portion_g) : null,
    off_barcode: form.value.off_barcode || null,
  })
  form.value.product_name=''; form.value.calories=''; form.value.protein=''; form.value.carbs=''; form.value.fat=''; form.value.off_barcode=''
  await load()
}
async function remove(id:number){ await deleteLog(id); await load() }

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <Utensils class="size-6" />
      <h1 class="text-page-title">Питание</h1>
      <span class="text-body text-muted-foreground">дневник + OFF + wger (опц.)</span>
    </div>

    <Card class="flex flex-col gap-3">
      <div class="flex flex-wrap gap-2 items-end">
        <div class="flex flex-col gap-1">
          <Label for="nutr-date">Дата</Label>
          <Input id="nutr-date" type="date" v-model="selectedDate" @change="load" />
        </div>
        <div class="ml-auto flex flex-wrap gap-2">
          <div class="rounded-input border px-3 py-2 text-body">Съедено: {{ summary?.intake_calories ?? 0 }} ккал · Б {{ Math.round(summary?.intake_protein ?? 0) }} У {{ Math.round(summary?.intake_carbs ?? 0) }} Ж {{ Math.round(summary?.intake_fat ?? 0) }}</div>
          <div v-if="summary?.burned_calories != null" class="rounded-input border px-3 py-2 text-body" :class="(summary?.net_calories ?? 0) < 0 ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'">Сожжено: {{ Math.round(summary.burned_calories) }} ккал · Баланс: <span class="font-medium">{{ summary.net_calories != null ? (summary.net_calories > 0 ? '+' : '') + Math.round(summary.net_calories) : '?' }} ккал</span></div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div class="flex flex-col gap-2 rounded-input border p-3">
          <div class="text-card-heading">Добавить приём</div>
          <div class="grid grid-cols-2 gap-2">
            <div class="flex flex-col gap-1">
              <Label>Приём</Label>
              <Select v-model="form.meal_type"><option value="breakfast">Завтрак</option><option value="lunch">Обед</option><option value="dinner">Ужин</option><option value="snack">Перекус</option></Select>
            </div>
            <div class="flex flex-col gap-1">
              <Label>Порция г</Label>
              <Input v-model="form.portion_g" type="number" />
            </div>
          </div>
          <Input v-model="form.product_name" placeholder="Продукт" />
          <div class="grid grid-cols-4 gap-2">
            <Input v-model="form.calories" placeholder="ккал" type="number" />
            <Input v-model="form.protein" placeholder="Б" type="number" />
            <Input v-model="form.carbs" placeholder="У" type="number" />
            <Input v-model="form.fat" placeholder="Ж" type="number" />
          </div>
          <div class="flex gap-2">
            <Button @click="add"><Plus class="size-4" /> Добавить</Button>
            <Button variant="outline" @click="onScanBarcode"><ScanLine class="size-4" /> Сканер</Button>
            <Button variant="ghost" @click="onManualBarcode">Вручную</Button>
          </div>
        </div>

        <div class="flex flex-col gap-2 rounded-input border p-3">
          <div class="flex gap-2">
            <Input v-model="offQuery" placeholder="Поиск OFF (напр. гречка, молоко)" @keydown.enter="doSearch" />
            <Button variant="secondary" @click="doSearch"><Search class="size-4" /> Найти</Button>
          </div>
          <div class="flex flex-col gap-2 max-h-[320px] overflow-auto">
            <button v-for="p in offResults" :key="p.barcode ?? p.product_name ?? ''" class="text-left rounded-input border p-2 hover:bg-muted" @click="fillFromOff(p)">
              <div class="flex gap-2">
                <img v-if="p.image_url" :src="p.image_url" class="h-12 w-12 object-cover rounded" />
                <div class="flex flex-col">
                  <span class="text-body font-medium">{{ p.product_name ?? 'Без названия' }}</span>
                  <span class="text-hint">{{ p.brands ?? '' }} · {{ p.calories_100g ?? '?' }} ккал/100г</span>
                </div>
              </div>
            </button>
            <div v-if="offResults.length===0" class="text-hint">Введи запрос и нажми Найти — подтянем из Open Food Facts без ключа.</div>
          </div>
        </div>
      </div>
    </Card>

    <Card class="flex flex-col gap-2">
      <div class="text-card-heading">Приёмы за {{ selectedDate }}</div>
      <div v-if="logs.length===0" class="text-hint">Пока пусто — добавь первый приём.</div>
      <div v-for="l in logs" :key="l.id" class="flex items-center justify-between rounded-input border px-3 py-2">
        <div class="flex flex-col">
          <span class="text-body">{{ l.meal_type }} · {{ l.product_name }} · {{ l.portion_g ?? '?' }}г</span>
          <span class="text-hint">{{ l.calories ?? '?' }} ккал · Б{{ l.protein ?? '?' }} У{{ l.carbs ?? '?' }} Ж{{ l.fat ?? '?' }} {{ l.off_barcode ? '· '+l.off_barcode : '' }}</span>
        </div>
        <Button size="sm" variant="destructive" @click="remove(l.id)"><Trash2 class="size-4" /></Button>
      </div>
    </Card>

    <Card class="p-3 text-hint">
      wger: в настройках питания появится блок «Синхронизация wger» — укажи URL + API-ключ (шифруется Fernet), тест соединения `/nutrition/wger/test`, синк по желанию. Базовый дневник работает без wger.
    </Card>

    <NutritionScannerDialog v-model:open="scannerOpen" @detected="onScanned" />
  </div>
</template>
