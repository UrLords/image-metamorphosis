import axios from "axios";
import { getIdToken } from "firebase/auth";
import { auth } from "../lib/firebase";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_PUBLIC_API_URL || import.meta.env.VITE_API_URL || "/api",
  timeout: 120000,
});

apiClient.interceptors.request.use(async (config) => {
  const user = auth.currentUser;

  if (user) {
    const token = await getIdToken(user, false);
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && auth.currentUser && !originalRequest?._retried) {
      originalRequest._retried = true;
      const token = await getIdToken(auth.currentUser, true);
      originalRequest.headers.Authorization = `Bearer ${token}`;
      return apiClient.request(originalRequest);
    }

    return Promise.reject(error);
  },
);

export default apiClient;
