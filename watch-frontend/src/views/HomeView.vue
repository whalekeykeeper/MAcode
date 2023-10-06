<template>
  <main>
    <HomeDemo />
  </main>
</template>


<!--<script setup>-->
<!--import TheWelcome from '../components/TheWelcome.vue'-->
<!--</script>-->

<script>
import {defineComponent} from 'vue'
import HomeDemo from "@/components/HomeDemo.vue";

export default defineComponent({
  name: "HomeView",
  components: {HomeDemo}
})
</script>

<style scoped>

</style>
