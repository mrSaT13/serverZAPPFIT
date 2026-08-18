<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'

const { t } = useI18n()
</script>

<template>
  <section class="flex flex-col items-center gap-3 text-center">
    <p class="text-display font-medium leading-none text-brand dark:text-brand-dark-foreground">
      404
    </p>
    <h1 class="text-2xl font-medium text-foreground">{{ t('app.notFound.title') }}</h1>
    <p class="max-w-sm text-sm text-muted-foreground">{{ t('app.notFound.message') }}</p>
    <Button as-child>
      <RouterLink :to="{ name: 'home' }">{{ t('app.notFound.action') }}</RouterLink>
    </Button>
  </section>
</template>
