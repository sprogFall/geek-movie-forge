import { Navigate, Route, Routes } from "react-router-dom";

import AssetsPage from "@/app/assets/page";
import CallLogsPage from "@/app/call-logs/page";
import ImageGenerationPage from "@/app/generations/images/page";
import TextGenerationPage from "@/app/generations/texts/page";
import VideoGenerationPage from "@/app/generations/videos/page";
import LoginPage from "@/app/login/page";
import HomePage from "@/app/page";
import ProjectsPage from "@/app/projects/page";
import ProvidersPage from "@/app/providers/page";
import RegisterPage from "@/app/register/page";
import TasksPage from "@/app/tasks/page";
import { ToastProvider } from "@/components/ui/toast-provider";
import { AuthProvider } from "@/lib/auth";
import { AppErrorBoundary } from "./error-boundary";

export function App() {
  return (
    <AppErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/assets" element={<AssetsPage />} />
            <Route path="/call-logs" element={<CallLogsPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/providers" element={<ProvidersPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/generations/images" element={<ImageGenerationPage />} />
            <Route path="/generations/texts" element={<TextGenerationPage />} />
            <Route path="/generations/videos" element={<VideoGenerationPage />} />
            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </AppErrorBoundary>
  );
}
