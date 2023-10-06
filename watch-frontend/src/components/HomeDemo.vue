<template>
  <v-container>
    <h1>Learning by watching</h1>
    <div>
<!--      <v-row>-->
<!--        <v-col  cols="12" md="6" xs="12">-->
<!--          <h1>Test1</h1>-->
<!--          <div class="bg-amber-accent-1">-->
<!--            <p class="ma-10 pa-10">Test</p>-->
<!--          </div>-->
<!--          <v-btn color="primary" class="">Button1</v-btn>-->
<!--          <v-btn color="secondary">Button2</v-btn>-->
<!--          <v-btn color="pink">Button3</v-btn>-->
<!--        </v-col>-->

<!--        <v-col cols="12" md="6" xs="12">-->
<!--          <h1>Test2</h1>-->
<!--        </v-col>-->
<!--      </v-row>-->

      <h3>Input a YouTube video url:</h3>
      <!--    <textarea v-model="word" placeholder="Input the word you want to translate."></textarea>-->
      <!--    <button class="button button1" @click="translate(word)">Translate</button>-->
      <!--    <ButtonComponent name="Translate" :color="'pink'" @button-click="translate(word)"/>-->

<!--      <textarea-and-button-component name="Input YouTube url" :color="'blue'" @button-click="getVideoID" />-->

      <div>
        <v-text-field v-model="video_url" :append-icon="'marker' ? 'mdi-map-marker' : 'mdi-map-marker-off'"
                      density="compact" label="Youtube Link" type="url"
                      name="url" @click:append="getVideo" @keyup.enter="getVideo(video_url)" clearable
                      >
        </v-text-field>
      </div>
      <!-- name, color, disabled -->
      <!-- Event: send; returns the text that was entered -->
      <div>
        <v-progress-circular indeterminate v-if="isLoading"/>
        <h4 v-else>{{this.video_url}}</h4>
      </div>

    </div>


<!--    <div>-->
<!--      <h3>Simplification:</h3>-->
<!--      <textarea v-model="text" placeholder="Input the text you want to simplify."></textarea>-->
<!--      <button class="button button2" @click="simplify(text)">Simplification</button>-->

<!--      <h4>{{this.simplified_text}}</h4>-->
<!--    </div>-->
  </v-container>

</template>

<script>
import {defineComponent} from 'vue'
import axios from 'axios'
import TextareaAndButtonComponent from "@/components/icons/TextareaAndButtonComponent.vue";
import api from '../api/backend-api';

export default defineComponent({
  name: "HomeDemo",
  components: {TextareaAndButtonComponent},
  data() {
    return {
      isLoading: false,
      video_url: 'https://www.youtube.com/watch?v=LMt8xm4t7XQ',
      video_id: '',
      word: '',
      translated_word: '',
      simplified_text: '',
      get_video_url: "http://127.0.0.1:8000/video/",
      // translation_url: 'https://api.dictionaryapi.dev/api/v2/entries/en/',
      // simplification_url: 'http://127.0.0.1:8000/simplification/',

    };
  },
  methods: {
    getVideo() {
      this.isLoading = true;
      console.log("The YouTube url is: ")
      console.log(this.video_url)

      const request = {video_url: this.video_url};
      api.getVideo(request)
          .then((resp) => {
            console.log("TRUE", resp);
            this.video_id = resp.data['video_id'];
            console.log(this.video_id)
            this.isLoading = false;
          })
          .catch((err) => {
            console.log("ERROR:", err);
            this.isLoading = false;
          })

    },
    // translate(word) {
    //   this.isLoading = true;
    //   console.log("The sent word is: ")
    //   console.log(word)
    //   const sentText = {text: String(word)};
    //   const headers = {
    //     "Content-Type": "application/json",
    //     "accept": "application/json"
    //   };
    //   // api.getTranslation(sentText)
    //   axios.post(this.translation_url, sentText, { headers })
    //       .then((resp) => {
    //
    //         this.translated_word = resp.data[0]['phonetic'];
    //         console.log(this.translated_word)
    //         this.isLoading = false;
    //       })
    //       .catch((err) => {
    //         console.log(err);
    //         this.isLoading = false;
    //       });
    // },

    // simplify(text) {
    //   console.log("The sent text is: ")
    //   console.log(text)
    //   const sentText = {text: String(text)};
    //   const headers = {
    //     "Content-Type": "application/json",
    //     "accept": "application/json"
    //   };
    //   // api.getTranslation(word).then((resp))
    //   axios.post(this.simplification_url, sentText, { headers })
    //       .then((resp) => {
    //
    //         console.log(resp)
    //         this.simplified_text = resp.data;
    //         console.log(this.simplified_text)
    //       })
    //       .catch((err) => {
    //         console.log(err);
    //       });
    // },

  },
})
</script>


<style scoped>

div {
  margin-bottom: 20px;
}

.button {
  //background-color: #4CAF50; /* Green */
  //border: none;
  //color: white;
  //padding: 20px;
  //text-align: center;
  //text-decoration: none;
  //display: inline-block;
  //font-size: 16px;
  //margin: 4px 2px;
  //cursor: pointer;
}

.button1 {border-radius: 2px;
  background-color: #ffc2d1;}
.button2 {border-radius: 50%;
  background-color: #c8b6ff}

</style>