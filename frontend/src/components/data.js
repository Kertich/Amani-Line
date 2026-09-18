export const updates = [
  {
    status: "Confirmed",
    title: "Water supply interruption — Estate B",
    detail:
      "Planned repair work will affect Estate B today from 9:00 AM to 4:00 PM.",
    source: "Mavoko Water notice",
    time: "Updated 18 min ago",
    icon: "💧",
  },
  {
    status: "Pending",
    title: "Road closure near Mlolongo Market",
    detail:
      "We are checking reports of a temporary closure near the market entrance.",
    source: "2 community reports",
    time: "Updated 42 min ago",
    icon: "🚧",
  },
  {
    status: "False",
    title: "Rumour: School closure tomorrow",
    detail: "This claim is not true. Schools in the area remain open as usual.",
    source: "Confirmed with school administration",
    time: "Updated 2 hr ago",
    icon: "📚",
  },
];

export const copy = {
  en: {
    nav: ["Home", "Community updates", "How it works"],
    greeting: "Good morning, Mlolongo.",
    sub: "Your trusted line for local information.",
    helper: "What would you like to do today?",
    actions: [
      {
        id: "report",
        icon: "↗",
        title: "Report something",
        text: "Share a rumour, issue, or concern.",
      },
      {
        id: "check",
        icon: "✓",
        title: "Check an update",
        text: "See what has been verified nearby.",
      },
      {
        id: "resolve",
        icon: "⌁",
        title: "Resolve a dispute",
        text: "Start a respectful resolution process.",
      },
    ],
    trusted: "Trusted by your community",
    note: "Updates are checked with local leaders, services and verified community members.",
  },
  sw: {
    nav: ["Mwanzo", "Taarifa za jamii", "Jinsi inavyofanya kazi"],
    greeting: "Habari za asubuhi, Mlolongo.",
    sub: "Njia yako ya kuaminika ya taarifa za eneo lako.",
    helper: "Ungependa kufanya nini leo?",
    actions: [
      {
        id: "report",
        icon: "↗",
        title: "Tuma taarifa",
        text: "Shiriki uvumi, tatizo, au wasiwasi.",
      },
      {
        id: "check",
        icon: "✓",
        title: "Angalia taarifa",
        text: "Tazama yaliyothibitishwa karibu nawe.",
      },
      {
        id: "resolve",
        icon: "⌁",
        title: "Tatua mzozo",
        text: "Anza mchakato wa heshima wa suluhu.",
      },
    ],
    trusted: "Inaaminika na jamii yako",
    note: "Taarifa hukaguliwa na viongozi wa eneo, huduma na wanajamii waliothibitishwa.",
  },
};
