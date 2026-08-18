<script setup lang="ts">
import { computed, useId } from 'vue'

import { Label } from '@/components/ui/label'

const props = withDefaults(
  defineProps<{
    /** Visible field label text. Omit to render only the control + messages. */
    label?: string
    /** Optional placeholder text for the control. */
    placeholder?: string
    /** Current error message; when set, the field is marked invalid. */
    error?: string
    /** Marks the field required (adds an asterisk and `aria-required` hint). */
    required?: boolean
    /** Optional helper text shown below the control when there is no error. */
    hint?: string
  }>(),
  { label: undefined, placeholder: undefined, error: undefined, required: false, hint: undefined },
)

// Stable, SSR-safe ids so the label, hint, and error associate with the control
// the slot renders. The consumer spreads `describedBy`/`fieldId` onto its input.
const fieldId = useId()
const errorId = `${fieldId}-error`
const hintId = `${fieldId}-hint`

const invalid = computed(() => Boolean(props.error))

/**
 * The `aria-describedby` value pointing at whichever message is visible: the
 * error when invalid, otherwise the hint (or `undefined` when neither exists).
 */
const describedBy = computed(() => {
  if (props.error) {
    return errorId
  }
  return props.hint ? hintId : undefined
})
</script>

<template>
  <div class="flex flex-col gap-1">
    <Label v-if="label" :for="fieldId">
      {{ label }}
      <span v-if="required" class="text-destructive" aria-hidden="true">*</span>
    </Label>

    <slot
      :field-id="fieldId"
      :described-by="describedBy"
      :invalid="invalid"
      :required="required"
      :placeholder="props.placeholder"
    />

    <p v-if="hint && !error" :id="hintId" class="text-hint">{{ hint }}</p>
    <p v-if="error" :id="errorId" class="text-field-error" role="alert" aria-live="polite">
      {{ error }}
    </p>
  </div>
</template>
