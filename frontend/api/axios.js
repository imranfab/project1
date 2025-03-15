import axios from 'axios';
import {store} from "../redux/store";
import {backendApiBaseUrl} from "../config";

export const axiosInstance = axios.create({
  baseURL: `http://127.0.0.1:8000`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

//console.log({backendApiBaseUrl})

axiosInstance.interceptors.request.use((config) => {
  config.headers['Content-Type'] = 'application/json';
  config.headers['X-CSRFToken'] = store.getState().auth.csrfToken;

  return config;
});
