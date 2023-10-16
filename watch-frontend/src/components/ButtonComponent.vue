<template>
  <div>
    <button class="button" :class="{blue : isBlue, pink: isPink}" @click="onClick">{{name}}</button>
  </div>
</template>

<script>
import {defineComponent} from 'vue'

export default defineComponent({
  name: "ButtonComponent",
  props: ["name", "color"],
  data() {
    return {
    };
  },
  computed: {
    isBlue() {
      return this.color === "blue";
    },
    isPink() {
      return this.color === "pink";
    }
  },
  methods: {
    onClick() {
      this.$emit("button-click");
    },
  }
})
</script>

<style scoped>
.button {
  border: none;
  color: white;
  padding: 20px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 4px 2px;
  cursor: pointer;
}

.pink {
  background-color: #ffc2d1;}
.lila {
  background-color: #c8b6ff}
.blue {
  background-color: deepskyblue;

}
</style>