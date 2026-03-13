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
        label: "Overview",
        description: "Pipeline summary and active pressure",
      },
    ],
  },
  {
    title: "Generation",
    items: [
      {
        href: "/generations/images",
        label: "Image",
        description: "Generate images from prompts",
      },
      {
        href: "/generations/videos",
        label: "Video",
        description: "Generate videos from prompts and images",
      },
      {
        href: "/generations/texts",
        label: "Text",
        description: "Scripts, captions and copywriting",
      },
    ],
  },
  {
    title: "Library",
    items: [
      {
        href: "/assets",
        label: "Assets",
        description: "Browse generated and uploaded media",
      },
      {
        href: "/providers",
        label: "Providers",
        description: "Manage AI model providers",
      },
    ],
  },
  {
    title: "Pipeline",
    items: [
      {
        href: "/projects",
        label: "Projects",
        description: "Story packages and revision states",
      },
      {
        href: "/tasks",
        label: "Tasks",
        description: "Queue activity across workers",
      },
    ],
  },
];

/** Flat list kept for backward compat */
export const navigationItems = navigationSections.flatMap((s) => s.items);
