export type NavItem = {
  href: string;
  label: string;
  description: string;
};

export type NavSection = {
  title: string | null;
  items: NavItem[];
};

export const navigationSections: NavSection[] = [
  {
    title: null,
    items: [
      {
        href: "/",
        label: "总览",
        description: "流水线概览与当前重点",
      },
    ],
  },
  {
    title: "生成",
    items: [
      {
        href: "/generations/images",
        label: "图片",
        description: "根据提示词生成图片",
      },
      {
        href: "/generations/videos",
        label: "视频",
        description: "根据提示词与参考图生成视频",
      },
      {
        href: "/generations/texts",
        label: "文本",
        description: "脚本、字幕与文案生成",
      },
    ],
  },
  {
    title: "资源库",
    items: [
      {
        href: "/assets",
        label: "素材",
        description: "浏览生成/上传的媒体素材",
      },
      {
        href: "/providers",
        label: "供应商",
        description: "管理 AI 模型供应商配置",
      },
    ],
  },
  {
    title: "流水线",
    items: [
      {
        href: "/projects",
        label: "项目",
        description: "故事包与版本进度",
      },
      {
        href: "/tasks",
        label: "任务",
        description: "查看任务执行情况",
      },
    ],
  },
];

/** Flat list kept for backward compat */
export const navigationItems = navigationSections.flatMap((s) => s.items);
