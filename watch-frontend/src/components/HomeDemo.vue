<template>
  <v-container>
    <h1>Learning by watching</h1>
    <div>

      <h3>Input a YouTube video url:</h3>

      <v-text-field v-model="youtube_url" :append-icon="'mdi-send'"
                    density="compact" label="Youtube Link" type="url"
                    name="url" @click:append="getVideo" @keyup.enter="getVideo(youtube_url)" clearable
      >
      </v-text-field>

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
                <span v-for="(word, index) in mono_cue.split(' ')" :key="index"
                      @click="getTranslation(word, mono_cue)"
                      class="text-h5 click">
                  {{ word }}&nbsp;
                </span>
              </div>
            </div>
          </div>

        </v-card>
        <v-card variant="outlined" class="mt-10" style="width: 100%;">
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

              <tr v-for="(item, i) in clicked" :key="i">
                <td>{{ item.word }}</td>
                <td>
                  <v-progress-circular indeterminate v-if="item.isTranslating" />
                  <span v-if="!item.isTranslating">{{ item.translation }}</span>
                </td>
                <td>{{ item.sentence }}</td>
              </tr>

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
      isTranslating: false,
      youtube_url: 'https://www.youtube.com/watch?v=LMt8xm4t7XQ',
      video_id: '',
      stream_url: '',
      vtt_url: '',
      currentCues: [],
      word: '',
      sentence: '',
      clicked: [],
    };
  },

  mounted() {
    // Check if this.$refs.videoPlayer is defined
    if (this.$refs.videoPlayer) {
      const videoPlayer = this.$refs.videoPlayer;

      // Add an event listener to the video element for the "click" event
      videoPlayer.addEventListener('click', (e) => {
        const progressBar = videoPlayer.getBoundingClientRect();
        const clickedPosition = e.clientX - progressBar.left;
        const progressBarWidth = progressBar.width;
        const duration = videoPlayer.duration;

        // Calculate the new time based on the clicked position and duration
        const newTime = (clickedPosition / progressBarWidth) * duration;

        // Set the video's currentTime to the new time
        videoPlayer.currentTime = newTime;
      });
    }
  },

  methods: {
    async getVideo() {
      this.isLoading = true;
      console.log("The YouTube url is: ")
      console.log(this.youtube_url)
      this.stream_url = 'http://127.0.0.1:8000/video/stream/'
      this.vtt_url = 'http://127.0.0.1:8000/video/vtt/'
      try{
        const response = await api.getVideo({ "video_url": this.youtube_url })
        if (response.status === 201) {
          this.video_id = response.data.video_id;
          this.stream_url = this.stream_url + this.video_id;
          this.vtt_url = this.vtt_url + this.video_id
          this.isLoading = false;
        } else {
          console.error('Failed to get the video/subtitle: ', response.statusText);
        }
      } catch (error) {
        console.error('Error: ', error);
        this.isLoading = false;
      }
    },
    updateCurrentCues() {
      const trackElement = this.$refs['bilingual-caption'];
      if (trackElement && trackElement.track && trackElement.track.activeCues) {
        const activeCues = trackElement.track.activeCues;
        this.currentCues = Array.from(activeCues);
        // console.log("this.currentCues: ", this.currentCues);
        // this.sendCuesToBackend();
      } else {
        this.currentCues = [];
      }
    },

    async getTranslation(clickedWord, clickedSentence) {

      const clickedItem = this.clicked.find(item => item.word === clickedWord && item.sentence === clickedSentence);
      if (!clickedItem) {
        // If not, push the item with empty translation and start translating
        this.clicked.push({ word: clickedWord, sentence: clickedSentence, isTranslating: true, translation: '' });
      try{
        const response = await api.getTranslation({ "word": clickedWord, "sentence": clickedSentence})
        if (response.status === 201) {
          const translation = response.data.translation;
          const clickedItem = this.clicked.find(item => item.word === clickedWord && item.sentence === clickedSentence);

          if (clickedItem) {
            clickedItem.translation = translation;
            clickedItem.isTranslating = false;
          }
        } else {
          console.error('Failed to get the translation: ', response.statusText);
        }
      } catch (error) {
        console.error('Error: ', error);
        this.isTranslating = false;
      }
      }
    },
  },
})
</script>

<style scoped>

div {
  margin-bottom: 20px;
}

.click:hover {
  background-color: yellow;
  cursor: pointer;
}

.center-container {
  display: flex;
  justify-content: center;
  width: 100%; /* Ensure the video spans the full width */
}

.custom-progress-bar {
  width: 100%;
  cursor: pointer;
  height: 10px;
  appearance: none;
  background: #ccc;
  border: none;
}

.custom-progress-bar::-webkit-progress-bar {
  background: #ccc;
}

.custom-progress-bar::-webkit-progress-value {
  background: #007bff;
}
</style>