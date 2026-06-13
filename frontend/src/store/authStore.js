import { create } from "zustand";

const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem("user") || "null"),
  token: localStorage.getItem("access_token") || null,
  isAuthenticated: !!localStorage.getItem("access_token"),

  login: (userData, token) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    set({ user: userData, token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    set({ user: null, token: null, isAuthenticated: false });
  },

  updateUser: (updatedUser) => {
    const merged = {
      ...JSON.parse(localStorage.getItem("user") || "{}"),
      ...updatedUser,
    };
    localStorage.setItem("user", JSON.stringify(merged));
    set({ user: merged });
  },
}));

export default useAuthStore;
