# Spoken per-person task alerts on staff's own phones + earbuds (BYOD), Easy FnB

Research date: 2026-11-04. Sources are current pages fetched on that date unless a date is given. Forum and Q&A material is mostly from 2023 and is marked that way.

## 1. PWA route: Web Push on Android Chrome and iOS Safari. Can it speak or play custom audio when closed or with the screen off?

### Takeaway
No. A PWA cannot reliably say a dynamic sentence ("Minh, bàn 7 gọi phục vụ") while it is closed, in the background or with the screen off, on either Android or iOS. A push can only show a notification with the system/channel default sound. Custom sounds are unsupported, `speechSynthesis` does not exist in a service worker, and audio plays only when a page is open. Use a PWA only for screen-on, page-open setups (the counter dashboard, or a phone kept unlocked on a lanyard), not for phones in pockets.

### Cited Findings
- The `sound` option of the Notification API is reportedly "not currently supported in any browser", so `showNotification({sound})` does not play a custom file. — [MDN browser-compat-data issue #23380](https://github.com/mdn/browser-compat-data/issues/23380) (via search summary)
- A Stack Overflow answer (archived 2023) says the notification `vibrate` option is ignored on Android O+, because notification channels made sound and vibration per-channel instead of per-notification. — [SO archive: play sound / vibrate in service worker](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/62261805/how-to-play-sound-in-service-worker-or-even-vibrate-in-chrome)
- The full range of audio APIs is available only from an open page, not from a service worker. The usual workaround is for the SW to `postMessage` an open client tab, which then plays the sound. This needs an open tab. — [SO archive 2023: play audio when push received in SW](https://kaweah.freedombox.rocks/kiwix/content/stackoverflow.com_en_all_2023-11/questions/39155856/how-to-play-audio-when-received-push-notification-in-service-worker-chrome)
- Some Android WebViews do not expose `speechSynthesis` at all (one report shows it "undefined" in a WebView on Chromium 138). Chrome on Android does support the Web Speech synthesis API in a normal page. — [Xibo community thread](https://community.xibo.org.uk/t/android-player-speechsynthesis-web-speech-api-unavailable-in-webview-chromium-138/38219); [TestMu speech-synthesis support](https://www.testmuai.com/learning-hub/speech-synthesis-api-browser-support/)
- iOS/iPadOS: Web Push needs the PWA to be installed from Safari (Add to Home Screen), iOS 16.4+. PWA notifications use the default sound and respect Silent mode. — [Darwin help: configure notifications](https://help.getdarwin.ai/en/articles/12193967-how-to-configure-notifications)
- On Apple's forums, developers say web push on iOS uses only the system default sound, and the web Notification standard has no field for a custom sound. — [Apple Dev Forums 736399](https://developer.apple.com/forums/thread/736399); [Apple Dev Forums 778080](https://developer.apple.com/forums/thread/778080)
- Some 2023 reports say iOS 16.4 PWA notifications arrived completely silent. Progressier's FAQ says "iOS does not support playing sounds for push notifications coming from PWAs." — [Apple Community 254759442 (2023)](https://discussions.apple.com/thread/254759442); [Progressier FAQ](https://intercom.help/progressier/en/articles/6753668-is-it-possible-for-a-pwa-to-play-a-sound-upon-receiving-a-push-notification)

### Inferences
- `speechSynthesis` exists on `window`, not in `ServiceWorkerGlobalScope`. None of the sources fetched say this directly, but it matches the "audio only from an open page" findings. So a push that arrives while the PWA is closed cannot produce speech.
- The only PWA setup that can speak is a page that is open, in the foreground, screen on, unlocked, receiving events over WebSocket/SSE (this is what the current prototype does). That is acceptable for the counter dashboard and possibly a hackathon demo phone. It does not meet the "phone in pocket, screen off" requirement.
- A degraded PWA fallback is still worth keeping. Android Chrome Web Push shows a heads-up notification with default sound and vibration (via the site's notification channel), which gives a beep but no speech.

### Gaps
- I found no published latency figures for Web Push (FCM-backed on Chrome, APNs-backed on Safari). Anecdotally it is usually sub-second to a few seconds when the device is not in deep Doze, but this is unverified.
- I did not fetch the WebKit "Web Push for Web Apps on iOS and iPadOS" blog post (2023) directly. The 16.4 requirement comes from the Darwin help page above.
- iOS 18/26 changes to PWA notification sounds: no current Apple statement found.

## 2. Native Android: FCM high-priority + foreground service + TextToSpeech with the screen off; Doze; OEM battery killers; Vietnamese TTS

### Takeaway
Native Android is the most reliable route for cheap Samsung/Xiaomi/Oppo/Vivo phones. During a shift, run a persistent foreground service that holds a WebSocket/MQTT connection to the Easy FnB backend for sub-second delivery. Use FCM high-priority data messages as a wake-up backup. Play pre-rendered or on-device Vietnamese TTS through the media/notification stream, which goes to the connected Bluetooth earbud. Always post a visible notification with each alert, or FCM will downgrade the app's priority. OEM battery killers (Xiaomi/Samsung 5/5, Oppo 4/5, Vivo 3/5) are the main risk, so staff onboarding must include battery-optimization and autostart settings.

### Cited Findings
- FCM high-priority messages: "FCM attempts to deliver high priority messages immediately", they can wake a sleeping device, and they "generally should result in user interaction with your app or its notifications." Normal-priority messages may be delayed while the device is in Doze. — [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android/message-priority)
- If high-priority messages don't lead to user-visible notifications, FCM may deprioritize them to normal or hand them to Google Play services. FCM evaluates "7 days of message behavior" per app instance. If notifications are disabled, messages get deprioritized. — [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android/message-priority)
- `onMessageReceived` gets "several seconds" to process the payload (slightly more for high priority). There is a brief exemption for expedited WorkManager jobs scheduled right after a high-priority message. — [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android/message-priority)
- Apps targeting Android 12+ cannot start foreground services from the background except in listed cases. Exemptions include receiving a high-priority FCM message and "The user turns off battery optimizations for your app". If FCM downgrades the message, starting an FGS throws `ForegroundServiceStartNotAllowedException`, so the app should check `RemoteMessage.getPriority() == PRIORITY_HIGH` first. — [Android: Restrictions on starting FGS from background](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- Android 14+ checks FGS-type permissions when the service is created. Types that need while-in-use permissions (microphone, camera, location) cannot be created from the background. Android 14/15 restrict which FGS types may start from `BOOT_COMPLETED`. — [Android: Restrictions on starting FGS from background](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- dontkillmyapp.com aggressiveness scores (higher = kills background apps more): Huawei 5, Xiaomi 5 (except Android One), OnePlus 5, Samsung 5 ("especially after Android P"), Oppo 4, Vivo 3, Realme 3, Google/Pixel 0. The page has no date. — [dontkillmyapp.com](https://dontkillmyapp.com/)
- On-device Google TTS (Speech Services by Google) downloads offline voice data per language (engine settings → Install voice data). A 2022 archived list includes Vietnamese (Vietnam). — [Resemble AI guide](https://www.resemble.ai/resources/google-tts-voice-data-installation); [Wikipedia snapshot, Mar 2022](https://webcf.waybackmachine.org/web/20220324110701/https://en.wikipedia.org/wiki/Speech_Services); [9to5Google, 2021](https://9to5google.com/2021/11/09/speech-services-by-google-reaches-10-billion-play-store-downloads/)

### Inferences
- Recommended Android architecture:
  - (a) When staff tap "Bắt đầu ca" (start shift), the app is in the foreground. It starts a foreground service with an ongoing notification ("Easy FnB đang nhận việc"). Starting from the foreground avoids the background-start restriction entirely.
  - (b) The service keeps a WebSocket to the backend. A task arrives in about 100–300 ms on restaurant Wi-Fi (estimate, not measured).
  - (c) On a task, the service plays a chime (single or double) plus speech, vibrates, and posts a high-importance notification with Accept/Done actions.
  - (d) The backend also sends an FCM high-priority data message as a backup in case the socket was killed. Each one must produce a visible notification so FCM keeps the high priority.
  - (e) Onboarding asks the user to whitelist the app from battery optimization. This also adds an FGS-start exemption.
- Speech source:
  - Option 1: play pre-rendered Chirp 3 HD clips (consistent, natural voice on every phone, no dependence on whether the vi-VN voice data is installed).
  - Option 2: on-device `TextToSpeech` with `Locale("vi","VN")` as a fallback. It works offline, but voice quality varies and the engine may be missing on some Oppo/Vivo builds (Pico TTS or vendor engines).
  - Pre-rendered audio also avoids mispronouncing staff names.
- Per-alert latency is dominated by network and device wake time, not TTS. Playing a cached clip starts almost immediately. On-device TTS init can add hundreds of ms on a cold engine (estimate).
- Wi-Fi sleep and Doze can break a WebSocket on a screen-off phone. The FCM high-priority backup covers that case. Watchdog: the backend should resend unacknowledged tasks via FCM after about 2 s.

### Gaps
- I did not verify current Android 14/15 rules on which FGS type fits a long-lived "receive tasks" service. Candidate types are `specialUse` (needs Play Console justification), `remoteMessaging`, `mediaPlayback` and `dataSync` (Android 15 limits dataSync to about 6 h per 24 h, so it does not fit a full shift). Check developer.android.com/develop/background-work/services/fgs/service-types.
- No measured FCM high-priority latency figures were found (Google publishes no SLA).
- Not verified: whether Speech Services by Google is pre-installed with the vi-VN voice on current Xiaomi HyperOS/ColorOS/FuntouchOS builds sold in Vietnam.
- Per-OEM steps (Xiaomi Autostart + "No restrictions"; Samsung "Never sleeping apps"; Oppo/Vivo "Allow background activity" + lock in recents) live on per-vendor dontkillmyapp pages that I did not fetch.
- Audio focus and routing: I found no source confirming defaults. The general rule (unverified here) is that `STREAM_MUSIC`/`USAGE_ASSISTANCE_NAVIGATION_GUIDANCE` and notification sounds route to a connected A2DP headset. Using `AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE` with transient-may-duck focus is the usual pattern for spoken prompts.

## 3. Native iOS: can an app speak dynamic text when a push arrives in the background? NSE, critical/time-sensitive, background audio, PushKit/CallKit, Push to Talk

### Takeaway
iOS does not let a backgrounded or terminated app run TTS when a normal push arrives. The workable pattern is to deliver the spoken sentence as the notification's custom sound. Each sound is a pre-rendered clip under 30 s, placed in the app bundle or `Library/Sounds` (app container or App Group). A Notification Service Extension can also attach a sound just before delivery. Pre-render "Minh, bàn 7 gọi phục vụ"-style clips server-side (Chirp 3 HD), sync them to `Library/Sounds` while the app is open, and send APNs alerts with `sound: "minh_ban07_phucvu.caf"` and `interruption-level: time-sensitive`. Push to Talk (iOS 16+) is the only Apple-sanctioned way to wake the app and play arbitrary audio in the background. It is a possible real-deployment upgrade ("dispatcher channel") but needs extra entitlement and App Review effort, and has known audio-session bugs.

### Cited Findings
- `UNNotificationSound`: for remote notifications, put the sound file name in `aps.sound`. "You can also use a notification service app extension to add a sound file to a notification shortly before delivery." — [Apple: UNNotificationSound](https://developer.apple.com/documentation/usernotifications/unnotificationsound)
- Sound files "must already be on the user's device". The system looks only in the app container's `/Library/Sounds`, an app shared group container's `/Library/Sounds`, and the main bundle. — [Apple: UNNotificationSound](https://developer.apple.com/documentation/usernotifications/unnotificationsound)
- Formats: Linear PCM, MA4 (IMA/ADPCM), µLaw, aLaw, in `aiff`, `wav` or `caf`. "Sound files must be less than 30 seconds in length. If the sound file is longer than 30 seconds, the system plays the default sound instead." Convert with `afconvert … -d ima4 -f caff`. — [Apple: UNNotificationSound](https://developer.apple.com/documentation/usernotifications/unnotificationsound)
- Critical sounds exist (`defaultCritical`, `criticalSoundNamed(_:withAudioVolume:)`), as do ringtone sounds (`defaultRingtone`, `ringtoneSoundNamed`). — [Apple: UNNotificationSound](https://developer.apple.com/documentation/usernotifications/unnotificationsound)
- Interruption levels (iOS 15+): `active` "lights up the screen, and can play a sound". `timeSensitive` also "breaks through system notification controls". `critical` "bypasses the mute switch to play a sound". `passive` plays no sound. — [Apple: UNNotificationInterruptionLevel](https://developer.apple.com/documentation/usernotifications/unnotificationinterruptionlevel)
- Push to Talk framework: "gives your apps the ability to provide user interface controls that allow your users to transmit audio from anywhere. It supplies an ephemeral Apple Push Notification service token so the system can wake your app in the background to handle incoming audio while a session is ongoing." The essentials article is titled "Build a walkie-talkie style app with system user interface controls". `PTChannelManager` supports channel restoration. — [Apple: Push to Talk](https://developer.apple.com/documentation/pushtotalk)
- WWDC22 "Enhance voice communication with Push to Talk" covers receiving audio in the background. The `channelManager(_:didActivate:)` delegate receives an `AVAudioSession` when the system activates audio, and incoming pushes are handled via `incomingPushResult`. — [WWDC22 session 10117](https://developer.apple.com/fr/videos/play/wwdc2022/10117/)
- Known issue (developer forum, undated): the first PTT push activates the audio session and plays, but a later incoming stream (for example about 5 s later, handled via `setRemoteParticipant`) did not reactivate the audio session. No confirmed fix was posted. — [Apple Dev Forums 812592](https://developer.apple.com/forums/thread/812592); related CallKit→PTT migration thread: [763289](https://developer.apple.com/forums/thread/763289)

### Inferences
- Phrase space for clips: 30 tables × ~6 task types (gọi phục vụ / tính tiền / dọn bàn / thêm nước / mang món / khẩn) = about 180 clips. Add an urgent variant (double chime) and you get about 360. Per-staff name prefix: either 20 staff × 360 = 7,200 clips (around 10–15 MB as IMA4 CAF at 2–3 s each; estimate), or a generic "Bàn 7 gọi phục vụ" clip plus the staff name in the notification title. Download clips into the App Group `Library/Sounds` at login. The chime can be baked into the start of each clip, since a notification has only one sound.
- Alternative: the NSE fetches a just-rendered clip and writes it to the App Group `Library/Sounds` before delivery. This allows fully dynamic text but adds a network round-trip of a few hundred ms to over 1 s, and NSE runtime is limited (Apple documents roughly 30 s; not re-verified here). Pre-sync is better for the 1–2 s target.
- A time-sensitive notification with a custom sound still respects the ring/silent switch (only `critical` bypasses it). Staff iPhones must have the ringer on, and "Time Sensitive" must be allowed for the app in Focus settings.
- PTT fit: technically it is the only iOS path that plays a server-originated audio stream in the background and routes it to earbuds like a walkie-talkie. The backend would act as a "remote participant" named e.g. "Easy FnB – Bàn 7". The downsides: users must join a channel each shift, the system PTT UI is shown, it needs the PTT entitlement plus the `audio` background mode, and the 5 s re-activation bug is a risk. Too risky for a 10-day hackathon. Worth a spike for production iOS.
- Keeping the app alive with the background `audio` mode (looping silent audio) to run AVSpeechSynthesizer is a known hack. App Review typically rejects it, and it drains the battery.

### Gaps
- Not fetched or verified: the Critical Alerts entitlement request process (Apple grants it to apps like health, public-safety and home-security on request; a restaurant pager would very likely be denied). CallKit/PushKit VoIP-push policy (PushKit VoIP pushes must report a CallKit call, so they cannot be misused for alerts). Live Activities limits (they update UI but cannot play custom speech; ActivityKit push updates can carry an alert sound). All of this is background knowledge only.
- Whether iOS routes notification sounds to a connected Bluetooth A2DP headset by default: no Apple source found.
- PTT App Review requirements (whether the app must offer real user-to-user voice): not found.

## 4. Cross-platform (Flutter / React Native): FCM + background TTS, effort for a 2–3 person team in ~10 days

### Takeaway
Flutter is the pragmatic choice (Google stack, single codebase). Use `firebase_messaging` for FCM/APNs and `flutter_tts` or `just_audio` for clips. A small native Kotlin foreground service, or a plugin such as `audio_service` or `flutter_foreground_task`, keeps Android alive with the screen off. Background message handlers on Android run in a separate isolate, so TTS/audio plugins must work there. For a 10-day hackathon, an Android-only Flutter (or plain Kotlin) build with clip playback is realistic. The iOS custom-sound path adds about 2–3 days, and PTT should not be attempted.

### Cited Findings
- `onBackgroundMessage` must be a top-level function, annotated `@pragma('vm:entry-point')` on Flutter 3.3.0+. "a separate isolate is created" for background messages, but only on Android. iOS/macOS do not use a separate isolate. Call `Firebase.initializeApp()` inside the handler if other Firebase services are used. — [Firebase: Receive messages in Flutter apps](https://firebase.google.com/docs/cloud-messaging/flutter/receive-messages)
- The `audio_service` plugin's README describes running `flutter_tts` inside a background audio task so it keeps working with the screen off. — [audio_service (GitHub fork)](https://github.com/michaelspeedcode/audio_service)

### Inferences
- Rough 10-day split for 2–3 people (estimate):
  - Day 1–2: Flutter app login, FCM token registration, foreground service with WebSocket.
  - Day 3–4: clip cache, playback via `just_audio`/`audioplayers`, chime and vibration patterns, Accept/Done actions.
  - Day 5: TTS fallback with `flutter_tts` (vi-VN).
  - Day 6–7: iOS APNs custom-sound path.
  - Day 8–10: OEM battery onboarding screen, testing on Samsung A, Redmi, Oppo, Vivo and iPhone.
- React Native equivalents exist (`@react-native-firebase/messaging`, `react-native-tts`, Notifee for foreground services), but Flutter matches the "prioritize Google" constraint.
- Do not rely on speaking from inside the FCM background isolate as the only path: it has only "several seconds" of processing time and may lose plugin registration. The foreground service plus clip playback is more robust.

### Gaps
- No GitHub issues were found that confirm or refute `flutter_tts` working with the screen off on MIUI/ColorOS from an FCM background isolate. Testing on real devices is required.
- Current versions and maintenance status of `flutter_foreground_task` and `audio_service` were not checked.

## 5. Alternative channels staff already use: Zalo OA/ZNS/Mini App, Telegram bots, Zello

### Takeaway
None of them can auto-play a spoken alert into an earbud with the screen off. A voice message on Zalo or Telegram arrives as an ordinary notification (default or chat sound) and must be tapped to play. Telegram is free and quick to prototype as a text/notification fallback channel, within 1 msg/s per chat and about 30 msg/s overall. Zalo ZNS costs about 200–300 VND per message through resellers, needs Zalo-approved templates, and is designed for business-to-customer notifications, so it is a poor fit for internal staff paging. Zello has a walkie-talkie model that does auto-play, but I could not verify its API or pricing.

### Cited Findings
- Telegram Bot API: "By default, bots are able to message their users at no cost". Limits: "In a single chat, avoid sending more than one message per second", about 30 messages/second overall, 20 messages/minute in a group. Paid broadcasts allow up to 1000 msg/s at 0.1 Stars per message above the free amount. — [Telegram Bots FAQ](https://core.telegram.org/bots/faq)
- ZNS reseller pricing: 8x8 lists a custom ZNS or service-review message at 200 VND, promotional at 300 VND, image +200 VND, and buttons 300–700 VND. — [8x8 messaging apps pricing](https://cpaas.8x8.com/en/pricing/messaging-apps-pricing/)
- GapOne (HubSpot marketplace) lists ZNS without a CTA at 300 VND, and a setup package (OA + SMS brandname + 10 templates) at 1,500,000 VND. — [GapOne listing](https://ecosystem.hubspot.com/marketplace/listing/gapone-225494)
- VietGuys (Oct 2023) puts a successful ZNS message at about 200 VND. — [VietGuys, 25/10/2023](https://vietguys.biz/en/martech/knowledge/zalo-zns-template-an-optimal-solution-for-customer-care-strategies-on-zalo)
- ZNS charges only for delivered messages, and notification messages must use predefined templates approved by Zalo. — [Infobip: Zalo compliance](https://www.infobip.com/docs/zalo/compliance-guidelines.md); [Infobip Zalo blog](https://www.infobip.com/blog/zalo-business)
- Zalo has moved some previously free functions to paid messages (VnExpress, on verification messages). — [VnExpress International](https://e.vnexpress.net/news/tech/zalo-demands-paid-messages-now-for-once-free-verification-4846582.html)

### Inferences
- Cost check for ZNS as a pager: 30 tables × ~20 tasks/table/day ≈ 600 alerts/day × 250 VND ≈ 150,000 VND/day ≈ 4.5M VND/month per restaurant. That is too expensive, and it is still silent text without speech. FCM/APNs are free.
- A Telegram bot is a cheap fallback for owners and managers (daily summaries, escalations), not for real-time spoken paging.
- A Zalo Mini App runs inside Zalo and shares the WebView/PWA limits on background audio (inference, not verified).

### Gaps
- Official Zalo ZNS price list (zalo.cloud / ZNS pricing page) for 2026: not retrieved. The figures above come from resellers.
- Zalo OA "tin tư vấn" (consultation messages to followers within an interaction window), its cost, and delivery latency: not verified.
- Whether Telegram or Zalo auto-play voice notes in the background: no source found (believed: no).
- Zello Work API/SDK (server-originated voice into channels) and its pricing: not researched within the tool budget.

## 6. Server-side TTS: Google Cloud TTS Vietnamese voices, pricing, caching; Gemini TTS alternative

### Takeaway
Google Cloud TTS has 40 vi-VN voices: 30 Chirp 3 HD, 2 Neural2, 4 WaveNet, 4 Standard. Chirp 3 HD costs $30 per 1M characters, and third-party listings report the first 1M characters free each month. Pre-rendering the entire phrase set (a few thousand clips) costs a few US dollars at most, or nothing within the free tier. Do this offline and cache the clips on phones instead of synthesizing per alert, which removes TTS latency from the 1–2 s budget. Gemini 3.8 Flash(-Lite) TTS supports Vietnamese and is an alternative for more expressive or custom voices (token-billed, about $0.81 per hour of audio).

### Cited Findings
- vi-VN voices (40):
  - Chirp3-HD (30): Achernar, Achird, Algenib, Algieba, Alnilam, Aoede, Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi. Example name: `vi-VN-Chirp3-HD-Kore` (F), `vi-VN-Chirp3-HD-Charon` (M).
  - Neural2: `vi-VN-Neural2-A` (F), `vi-VN-Neural2-D` (M).
  - WaveNet: `vi-VN-Wavenet-A/B/C/D`.
  - Standard: `vi-VN-Standard-A/B/C/D`.
  — [Google Cloud TTS: Supported voices](https://docs.cloud.google.com/text-to-speech/docs/voices)
- Chirp 3 HD lists vi-VN as supported. It is GA in the global, us and eu locations, plus asia-southeast1, europe-west2 and asia-northeast1. — [Google Cloud: Chirp 3 HD voices](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)
- Pricing: Chirp 3 HD is $0.00003 per character ($30 per 1M characters), and Instant custom voice is $60 per 1M. — [Google Cloud TTS pricing (es-419)](https://cloud.google.com/text-to-speech/pricing?hl=es_419) (via search snippet; the page did not render in fetch)
- Standard and WaveNet: $4 per 1M characters. Studio: $160 per 1M. First 1M Chirp 3 HD characters free per month. — [diyai.io 2026 pricing summary](https://diyai.io/ai-tools/audio-generation/google-cloud-text-to-speech-pricing/) (third-party; free tier not confirmed on Google's page in my fetch)
- Gemini TTS models on the AI Studio docs page (fetched 2026-11-04): `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-3.1-flash-tts-preview`, `gemini-2.5-pro-preview-tts`. Vietnamese is marked supported for 3.8 Flash TTS and 3.8 Flash-Lite TTS. The library has 30 prebuilt voices, plus an extended library and voice design/replication. — [Google AI Studio docs: Speech generation](https://aistudio.google.com/docs/speech-generation)
- Gemini TTS output: WAV, 24 kHz mono 16-bit PCM (unary), or raw PCM when streaming. μ-law/A-law 8 kHz are also available, and `sample_rate` is configurable. Streaming returns audio as it is synthesized. The docs give no latency figures. — [Google AI Studio docs: Speech generation](https://aistudio.google.com/docs/speech-generation)
- Gemini 3.8 Flash TTS pricing (via search summary of Google's Cloud pricing page): input $0.50 per 1M text tokens and audio output $9.00 per 1M tokens through 2026-12-31, rising to $1.00 / $18.00 from 2027-01-01. Flash-Lite TTS output is $6 → $12 per 1M. Audio is 25 tokens/s, so about $0.81 per hour of audio. — [Google Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing/?authuser=8); [eesel.ai summary](https://eesel.ai/blog/gemini-3-8-flash-tts-pricing) (third-party; verify)

### Inferences
- Caching math at Chirp 3 HD: 360 generic clips × ~25 characters ≈ 9,000 characters ≈ $0.27. With 20 staff names: 7,200 clips × ~30 characters ≈ 216,000 characters ≈ $6.50, or within the 1M free tier if that tier applies. Re-render only when staff join.
- Clip pipeline: request `LINEAR16` or `MULAW` output, then add the chime and convert to IMA4 `.caf` for iOS notification sounds (Apple's accepted codecs) and to `.ogg`/`.mp3` for Android. Using the same voice (e.g. `vi-VN-Chirp3-HD-Kore`) everywhere keeps the brand voice consistent.
- If a live per-alert synthesis path is needed (free-form text), Chirp 3 HD supports streaming synthesis. Latency was not measured here. The asia-southeast1 endpoint is closest to Vietnam.
- Neural2 has only 2 vi-VN voices, and its price was not confirmed in this research.

### Gaps
- Official per-tier prices for Neural2 and Chirp HD, and official free-tier amounts per voice type, could not be extracted (the Google pricing page truncated on fetch).
- No measured time-to-first-audio figures for Chirp 3 HD or Gemini TTS were found.
- The "Gemini 3.8" model naming comes from the fetched AI Studio page and pricing snippets. Re-verify the model IDs and preview/GA status at build time.

## 7. Bluetooth earbud practicalities (single earbud for a whole shift, battery, latency, routing)

### Takeaway
I found no authoritative sources within the tool budget. Treat all earbud figures as assumptions to test on site.

### Cited Findings
- No sourced findings were obtained for earbud battery life, single-bud mode, Bluetooth latency, or default routing of notification audio.

### Inferences
- Design for one earbud in mono with a short (about 0.3–0.5 s) chime before speech. Many cheap TWS buds enter a power-save state, and the first few hundred ms of audio after idle can be clipped. A leading chime or silence padding protects the spoken words (common practitioner experience; unverified).
- Plan for batteries running out within a shift. Use a two-bud rotation (one charges in the case while the other is worn), and keep vibration plus a visible notification as a redundant channel.

### Gaps
- Battery life of cheap TWS buds in VN (Xiaomi Redmi Buds, Soundpeats, QCY, Baseus). Manufacturer specs are typically around 4–8 h per bud, but this was not verified here.
- Typical Bluetooth A2DP latency (commonly cited 100–300 ms) is not verified. It matters little against a 1–2 s budget.
- Whether Android and iOS route notification sounds and TTS to the earbud by default, and whether some OEMs play notification sounds on both the speaker and the headset, is unverified and needs device testing.

## 8. Shared counter dashboard (existing tablet/TV/POS PC browser, keep the screen awake, kiosk)

### Takeaway
The counter dashboard is the one place where the current web approach (open page, WebSocket, Web Speech API or pre-rendered clips) works. The page stays open and in the foreground on an existing tablet, smart TV browser or POS PC. Keep the screen on with the Screen Wake Lock API or device settings, and lock it to the page with Android screen pinning or a kiosk/fullscreen browser mode. I did not fetch sources for these specifics.

### Cited Findings
- From an open page (not a service worker), the full set of audio APIs is available. — [SO archive 2023](https://kaweah.freedombox.rocks/kiwix/content/stackoverflow.com_en_all_2023-11/questions/39155856/how-to-play-audio-when-received-push-notification-in-service-worker-chrome)
- Chrome supports Speech Synthesis on Windows, macOS, Linux, ChromeOS and Android. Some Android WebViews (for example digital-signage players) do not expose it. — [TestMu](https://www.testmuai.com/learning-hub/speech-synthesis-api-browser-support/); [Xibo community](https://community.xibo.org.uk/t/android-player-speechsynthesis-web-speech-api-unavailable-in-webview-chromium-138/38219)

### Inferences
- Use pre-rendered Chirp 3 HD clips on the dashboard too, rather than Web Speech. The `vi-VN` voice availability of `speechSynthesis` depends on the OS (a Windows POS PC may lack a Vietnamese voice). Clips sound the same on every device.
- Autoplay policy: the browser needs one user tap ("Bật âm thanh") after load before audio can play. Plan for this on every reboot.

### Gaps
- Not fetched: the Screen Wake Lock API support matrix (`navigator.wakeLock.request('screen')`), Chrome kiosk flags, Android screen pinning/Lock Task mode, and smart-TV browser capabilities.

## 9. Recommendation: hackathon demo vs. real deployment

### Takeaway
- **Hackathon (14/11/2026, ~10 days):** build a native Android app (Kotlin or Flutter) with a shift-long foreground service, a WebSocket to the backend, and FCM high-priority data messages as backup. Play cached Chirp 3 HD clips (chime + "Minh, bàn 7 gọi phục vụ") to the paired earbud, plus vibration and a visible notification with Accept/Done. For iPhones, send APNs time-sensitive notifications whose custom sound is the pre-rendered clip. Keep the web prototype as the counter dashboard.
- **Real deployment:** keep the same architecture, add an OEM battery-whitelist onboarding wizard, server-side acknowledgement with timed re-assignment, and a Telegram text fallback for managers. Evaluate the iOS Push to Talk framework only if iOS staff need richer audio. Avoid ZNS and PWA push for paging.

### Cited Findings
- The building blocks are documented: FCM high-priority delivery, a visible-notification requirement, and the FGS start exemption ([Firebase](https://firebase.google.com/docs/cloud-messaging/android/message-priority), [Android](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)). iOS custom notification sounds under 30 s from the App Group `Library/Sounds` ([Apple](https://developer.apple.com/documentation/usernotifications/unnotificationsound)). Time-sensitive interruption level ([Apple](https://developer.apple.com/documentation/usernotifications/unnotificationinterruptionlevel)). vi-VN Chirp 3 HD voices at $30/1M characters ([Google voices](https://docs.cloud.google.com/text-to-speech/docs/voices), [pricing](https://cloud.google.com/text-to-speech/pricing?hl=es_419)).
- OEM risk: Xiaomi and Samsung 5/5, Oppo 4/5, Vivo 3/5 on dontkillmyapp. — [dontkillmyapp.com](https://dontkillmyapp.com/)

### Inferences
- Comparison summary:

| Route | Speaks with screen off / app closed | Latency | Cost | Effort (10 days) | Verdict |
|---|---|---|---|---|---|
| PWA + Web Push | No (default beep only; iOS needs A2HS, may be silent) | ~1–3 s (unmeasured) | Free | Low | Dashboard/demo only |
| Native Android (FGS + WebSocket + FCM) | Yes (clips or on-device TTS) | <1 s socket; FCM backup | Free (FCM) | Medium | **Primary** |
| Native iOS (APNs + custom-sound clip) | Yes, as the notification sound (fixed clips, ringer on) | ~1 s typical (unmeasured) | Free (APNs) + $99/yr dev account | Medium | **Primary for iPhone** |
| iOS Push to Talk | Yes (live audio) | Low | Entitlement + review risk | High | Post-hackathon spike |
| Flutter/RN | Same as native, with plugin caveats | Same | Free | Medium (one codebase) | Recommended toolkit |
| Zalo ZNS / OA | No (text; tap to play) | Unknown | ~200–300 VND/msg + setup | Medium (template approval) | Not for paging |
| Telegram bot | No (tap to play voice) | Typically fast (unmeasured) | Free (1 msg/s per chat) | Low | Manager fallback |

- Demo risk control: bring 2–3 pre-configured phones (one Samsung A, one Redmi) with battery optimization already disabled, buds charged, and the app in "Bắt đầu ca" mode. Show the screen-off delivery live, and show acknowledgement by double-tap on the bud or the notification action.

### Gaps
- The Apple Developer Program fee (about US$99/yr) and TestFlight distribution needs for the iPhone demo are background knowledge, not fetched.
- No field data on end-to-end latency (camera event → earbud) for any route. This should be measured during the hackathon build.
