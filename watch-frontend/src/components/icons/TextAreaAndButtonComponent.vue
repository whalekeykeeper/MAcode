
<template>
  <div>
    <textarea v-model="input" :disabled=dis></textarea>
    <button class="button" :class="{pink: isPink, blue: isBlue}" @click="onClick" >{{name}}</button>
    <!--    <p>{{isDisabled}}</p>-->
  </div>
</template>

<script>
import {defineComponent} from 'vue'

export default defineComponent({
  name: "TextareaAndButtonComponent",
  props: ["name", "color", "dis"],
  data() {
    return {
      input: '',
    };
  },
  computed: {
    isBlue() {
      return this.color === "blue";
    },
    isPink() {
      return this.color === "pink";
    },
  },
  methods: {
    onClick() {
      this.$emit("button-click", this.input);
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
  background-color: deepskyblue;}

</style>