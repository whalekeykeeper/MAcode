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

      <v-text-field v-model="youtube_url" :append-icon="'mdi-send'"
                    density="compact" label="Youtube Link" type="url"
                    name="url" @click:append="getVideo" @keyup.enter="getVideo(youtube_url)" clearable
      >
      </v-text-field>
      <!-- name, color, disabled -->
      <!-- Event: send; returns the text that was entered -->
      <div>
        <v-progress-circular indeterminate v-if="isLoading"/>
        <h4 v-else>{{this.youtube_url}}</h4>
      </div>


      </div>


      <v-row>
        <v-card class="mt-1" style="min-height: 550px">
          <video
              ref="video-player"
              width="800"
              height="450"
              controls
              :src="stream_url"
              type="video/mp4"
              crossorigin="anonymous"
              @timeupdate="updateCurrentCues" >

            <track
                default
                kind="metadata"
                label="BILINGUAL"
                srclang="bi"
                :src="vtt_url"
                ref="bilingual-caption"
            />

          </video>

          <div>
            <div v-for="(cue, index) in currentCues" :key="index">
              <div v-for="(mono_cue,index) in cue.text.split('§')" :key="index">
                <span v-for="(word, index) in mono_cue.split(' ')" :key="index">
                  {{ word }}&nbsp;
                </span>
              </div>
            </div>
          </div>

        </v-card>
        <v-card variant="outlined" class="mt-10">
          <v-card-title class="text-left">Words:</v-card-title>
          <v-card-subtitle class="text-left">Words to be learned</v-card-subtitle>
          <v-table>
            <thead>
            <tr>
              <th class="text-left">
                Word
              </th>
              <th class="text-left">
                Translation
              </th>
              <th class="text-left">
                Sentence
              </th>
            </tr>
            </thead>
            <tbody>

<!--            <tr v-for="(item, i) in this.clicked" :key="i">-->
<!--              <td>{{ item[0] }}</td>-->
<!--              <td>{{ item[1] }}</td>-->
<!--              <td>{{ item[2] }}</td>-->
<!--            </tr>-->
            </tbody>
          </v-table>
        </v-card>
        </v-row>
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
      youtube_url: 'https://www.youtube.com/watch?v=LMt8xm4t7XQ',
      video_id: '',
      stream_url: '',
      vtt_url: '',
      word: '',
      get_video_url: "http://127.0.0.1:8000/video/",
      currentCues: [],
      tokenizedCues: [],
    };
  },
  methods: {
    async getVideo() {
      this.isLoading = true;
      console.log("The YouTube url is: ")
      console.log(this.youtube_url)
      this.stream_url = 'http://127.0.0.1:8000/video/stream/'
      this.vtt_url = 'http://127.0.0.1:8000/video/vtt/'
      // const request = {video_url: this.video_url};
      // api.getVideo(request)
      //     .then((resp) => {
      //       console.log("TRUE", resp);
      //       this.video_id = resp.data['video_id'];
      //       console.log(this.video_id)
      //       this.isLoading = false;
      //     })
      //     .catch((err) => {
      //       console.log("ERROR:", err);
      //       this.isLoading = false;
      //     })
      try{
        const response = await api.getVideo({ "video_url": this.youtube_url })
        console.log(response.status)
        if (response.status === 201) {
          this.video_id = response.data.video_id;
          this.stream_url = this.stream_url + this.video_id;
          this.vtt_url = this.vtt_url + this.video_id
          this.isLoading = false;
        } else {
          console.error('Failed to get the video: ', response.statusText);
        }
      } catch (error) {
        console.error('Error: ', error);
        this.isLoading = false;
      }

    },
    updateCurrentCues() {
      const trackElement = this.$refs['bilingual-caption'];
      console.log("trackElement in updateCurrentCues(): ")
      console.log(trackElement);
      if (trackElement && trackElement.track && trackElement.track.activeCues) {
        const activeCues = trackElement.track.activeCues;
        this.currentCues = Array.from(activeCues);
        // console.log("this.currentCues: ", this.currentCues);
        // this.sendCuesToBackend();
      } else {
        this.currentCues = [];
      }
    },

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