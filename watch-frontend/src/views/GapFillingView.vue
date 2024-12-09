<template>
  <div class="container mt-4">
    <div v-if="loading" class="text-center">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <div v-else-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <div v-else-if="exercises.length > 0" class="card">
      <div class="card-header bg-primary text-white text-center">
        Gap Filling Task
      </div>

      <div class="card-body">
        <h3 class="card-subtitle mb-3 text-left">
          {{ isSubmitted ? '' : 'Please select the most fitting word based on the context and given translation.' }}
        </h3>
        <div class="empty-row"></div>

        <div v-if="!isSubmitted">
          <div class="exercise-content mb-3">
            <p class="fw-bold text-left gapped-sentence">
              {{ currentIndex + 1 }}. {{ currentExercise.gapped_sentence }}
            </p>

            <div class="empty-row"></div>
            <div class="empty-row"></div>

            <div class="options d-flex justify-content-start">
              <button
                  v-for="(option, index) in currentExercise.options"
                  :key="option"
                  class="btn btn-outline-primary m-2 option-btn option-text"
                  :class="{
                  'btn-primary text-white': selectedOption === option,
                  'btn-outline-primary': selectedOption !== option,
                  'text-primary': selectedOption === option
                }"
                  @click="selectOption(option)"
              >
                {{ String.fromCharCode(65 + index) }}. {{ option }}&nbsp;&nbsp;&nbsp;&nbsp;
              </button>
            </div>

            <div class="empty-row"></div>
            <div class="empty-row"></div>
            <div class="empty-row"></div>
            <div class="empty-row"></div>
            <div class="empty-row"></div>
          </div>

          <div class="d-flex justify-content-between align-items-center mt-3">
            <v-btn
                v-if="currentIndex > 0"
                class="btn btn-secondary"
                @click="goToPrevious"
            >
              Previous
            </v-btn>
            <div v-else class="invisible"></div>

            <v-btn
                v-if="currentIndex < MAX_EXERCISES - 1"
                class="btn btn-primary"
                :disabled="!selectedOption"
                @click="goToNext"
            >
              Next
            </v-btn>

            <v-btn
                v-if="currentIndex === MAX_EXERCISES - 1"
                class="btn btn-success"
                :disabled="!selectedOption"
                @click="submitExercises"
            >
              Submit
            </v-btn>
          </div>
        </div>

        <div v-else>
          <div
              v-for="(exercise, index) in exercises.slice(0, MAX_EXERCISES)"
              :key="exercise.id"
              class="mb-3"
          >
            <p class="fw-bold text-left gapped-sentence">
              {{ index + 1 }}. {{ exercise.gapped_sentence }}
            </p>
            <div class="options d-flex flex-wrap">
              <button
                  v-for="(option, idx) in exercise.options"
                  :key="option"
                  class="btn m-1 option-text"
                  :class="{
                  'btn-success': option === exercise.correct_option,
                  'btn-danger': option === exercise.user_selected && option !== exercise.correct_option,
                  'btn-outline-secondary':
                    option !== exercise.correct_option &&
                    option !== exercise.user_selected
                }"
                  disabled
              >
                {{ String.fromCharCode(65 + idx) }}. {{ option }}&nbsp;&nbsp;&nbsp;&nbsp;
              </button>
            </div>
          </div>

          <div class="empty-row"></div>
          <div class="empty-row"></div>

          <div class="mt-4 bg-light p-3 statistic-text">
            <p class="fw-bold">
              In the above gap filling task, you chose
              {{ exercises.filter(e => e.user_selected === e.correct_option).length }}
              out of {{ MAX_EXERCISES }} successfully.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center">
      <p>No exercises available. Try generating new ones!</p>
      <v-btn
          class="btn btn-primary"
          @click="generateExercises"
      >
        Generate Exercises
      </v-btn>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "GapFillingView",
  data() {
    return {
      exercises: [],
      loading: false,
      error: null,
      currentIndex: 0,
      selectedOption: null,
      isSubmitted: false,
      MAX_EXERCISES: 5,
      timer: null
    };
  },
  computed: {
    currentExercise() {
      return this.exercises[this.currentIndex];
    }
  },
  methods: {
    async fetchExercises() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get("http://localhost:8000/gapfilling/");
        this.exercises = response.data.slice(0, this.MAX_EXERCISES);
        this.resetCurrentExercise();
      } catch (err) {
        this.error = "Failed to fetch exercises. Please try again.";
        console.error(err);
      } finally {
        this.loading = false;
      }
    },
    async generateExercises() {
      this.loading = true;
      this.error = null;
      try {
        await axios.post("http://localhost:8000/gapfilling/generate");
        this.fetchExercises();
      } catch (err) {
        this.error = "Failed to generate exercises. Please try again.";
        console.error(err);
      } finally {
        this.loading = false;
      }
    },
    async submitAnswer(exercise) {
      try {
        const response = await axios.post(
            `http://localhost:8000/gapfilling/${exercise.id}/correct`,
            {
              is_correct: exercise.user_selected === exercise.correct_option
            }
        );
        return response.data;
      } catch (err) {
        console.error(err);
        return null;
      }
    },
    selectOption(option) {
      this.selectedOption = option;
      this.exercises[this.currentIndex].user_selected = option;
      clearTimeout(this.timer);
      this.timer = setTimeout(this.goToNext, 500);
    },
    goToNext() {
      if (this.currentIndex < this.MAX_EXERCISES - 1) {
        this.currentIndex++;
        this.selectedOption = this.exercises[this.currentIndex].user_selected || null;
      }
    },
    goToPrevious() {
      if (this.currentIndex > 0) {
        this.currentIndex--;
        this.selectedOption = this.exercises[this.currentIndex].user_selected || null;
      }
    },
    resetCurrentExercise() {
      this.currentIndex = 0;
      this.selectedOption = null;
      this.isSubmitted = false;
    },
    async submitExercises() {
      if (!this.selectedOption) return;

      for (const exercise of this.exercises.slice(0, this.MAX_EXERCISES)) {
        await this.submitAnswer(exercise);
      }

      this.isSubmitted = true;
    }
  },
  created() {
    this.fetchExercises();
  }
};
</script>

<style scoped>
.option-btn {
  min-width: 200px;
}
.d-flex {
  display: flex;
}
.justify-content-between {
  justify-content: space-between;
}
.align-items-center {
  align-items: center;
}
.mt-3 {
  margin-top: 1rem;
}
.text-primary {
  color: blue !important;
}
.bg-light {
  background-color: #f8f9fa !important;
}
.empty-row {
  height: 1rem;
}
.gapped-sentence {
  font-size: 1.5rem;
}
.option-text {
  font-size: 1.5rem;
}
.statistic-text {
  font-size: 1.5rem;
  font-weight: bold;
}
</style>