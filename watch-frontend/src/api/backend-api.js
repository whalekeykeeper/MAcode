import axios from 'axios';

const axiosApi = axios.create({
    baseURL: 'http://localhost:8000/',
    // headers: {'Content-Type': "application/json"},
})

export default {

    getVideo(request) {
        return axiosApi.post(`/video`, request);
    },
    getTranslation(request) {
        return axiosApi.post(`/translation`, request)
    },
    async getOrCreateUser() {
        const userUUID = localStorage.getItem("user_uuid");
        const headers = userUUID ? { "X-User-UUID": userUUID } : {};
        const response = await axiosApi.post("/get-or-create-user/", {}, { headers });
        if (!userUUID) {
            localStorage.setItem("user_uuid", response.data.uuid);
        }
        return response.data;
    }

}
