<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <v-app>
    <v-app-bar>
      <v-app-bar-title @click="$router.push('/')" style="cursor: pointer;">Learning by Watching</v-app-bar-title>
      <v-btn to="/about">About</v-btn>
      <v-btn to="/gapfilling">Exercises</v-btn>
    </v-app-bar>
    <v-main>
      <RouterView />
    </v-main>
  </v-app>
</template>

<style scoped>
</style>
