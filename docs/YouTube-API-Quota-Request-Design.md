# YouTube Data API v3 — Quota Extension Design Document

**Application name:** Archive to YouTube  
**Document purpose:** Design document in support of a YouTube API Services quota extension request  
**API in use:** YouTube Data API v3  
**Primary audience:** Creators  

---

## 1. Application overview

**Archive to YouTube** is an open-source tool that lets **creators** (individuals and small organizations) upload **audio collections from archive.org** to **their own YouTube channels** as videos and playlists. Users authenticate with YouTube via OAuth 2.0 and upload content only to channels they own; there is no server-side channel or bulk upload on behalf of third parties.

**Typical use case:** A user has an archive.org URL for a live concert or album (e.g. 20 tracks). The tool:

1. Fetches metadata and audio file URLs from archive.org (no YouTube API).
2. Downloads audio, generates video files (static image + audio) locally.
3. Uploads each video to the **user’s** YouTube channel and creates a single playlist for that collection.

All uploads are **user-initiated**, **one collection per run**, and content is **cultural/archival** (concerts, lectures, historical recordings) from the public domain or permissively licensed on archive.org.

---

## 2. YouTube API usage

We use **YouTube Data API v3** only. No Analytics, Reporting, Content ID, Embeds, or Live Streaming APIs.

### 2.1 Operations used

| Operation | Purpose | Quota cost (units) |
|-----------|---------|---------------------|
| `videos.insert` | Upload one video (metadata + file) | 1,600 |
| `playlists.insert` | Create one playlist per collection | 50 |
| `playlistItems.insert` | Add each video to the playlist (one call per video) | 50 |
| `videos.update` | Set video privacy (e.g. public) when user chooses to publish | 50 |
| `playlists.update` | Set playlist privacy when user publishes | 50 |
| `videos.list` | Check existing videos (avoid duplicates) | 1 |
| `playlists.list` | Resolve playlist / list playlists | 1 |

(Quota costs per [YouTube API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost).)

### 2.2 Typical run (one archive.org collection)

Example: **one collection = 20 tracks**.

- **Upload phase:**  
  - 20 × `videos.insert` = 20 × 1,600 = **32,000** units  
  - 1 × `playlists.insert` = **50** units  
  - 20 × `playlistItems.insert` = 20 × 50 = **1,000** units  
  - A few `videos.list` / `playlists.list` = on the order of **10** units  

- **Publish phase (user chooses “make public”):**  
  - 20 × `videos.update` = 20 × 50 = **1,000** units  
  - 1 × `playlists.update` = **50** units  

**Total for one 20-track collection (upload + publish): ~34,100 units.**

So **one user, one typical run**, already exceeds the **default 10,000 units/day** quota. A single run can hit the limit partway through (e.g. after uploading a few videos or after making only some videos public), which is why we are requesting a quota increase.

---

## 3. Why we need a quota increase

- **Default quota:** 10,000 units per day per project.  
- **One run:** ~34,000+ units for a single 20-track collection (upload + playlist + publish).  
- **Result:** A single user cannot complete one full collection in one day under the default quota. Operations fail with `403 quotaExceeded` once the 10,000 limit is reached.

We are **not** running automated or bulk uploads for many channels. Each run is:

- Triggered by a **single creator** in their own environment (CLI or our web UI).
- Authenticated with **that creator’s** Google account (OAuth 2.0).
- Uploading only to **that creator’s** channel.

A higher quota is needed so that:

1. **One creator** can finish **one collection** (e.g. 20–30 tracks) in a single day without hitting the limit.  
2. **A small number of concurrent users** (e.g. low tens) can each do **one collection per day** without exhausting quota.

---

## 4. Primary audience: Creators

The primary audience is **Creators**:

- Individuals who want to preserve or share archive.org audio (concerts, lectures, radio, etc.) on **their own** YouTube channel.
- Small archives or cultural organizations that run the tool occasionally to publish **one** collection at a time to **their** channel.

We do **not** target:

- Viewers-only applications.  
- Advertisers or enterprises.  
- Unattended or cross-account bulk uploads.

Every upload is to the authenticated user’s channel, with the user in control of what is uploaded and when.

---

## 5. Approximate usage and requested quota

- **Expected usage model:**  
  - Small user base (e.g. dozens to low hundreds of users over time).  
  - Each user runs the tool infrequently (e.g. a few collections per month).  
  - Each run = one archive.org collection → one playlist + N videos on that user’s channel.

- **Quota need (example):**  
  - To support **10 users** each completing **one 20-track collection per day**:  
    10 × ~34,000 ≈ **340,000** units/day.  
  - To support **10 users** each completing **one 20-track collection per week** (spread over the week):  
    ~340,000 / 7 ≈ **50,000** units/day.  

We are asking for a **quota extension** so that at least **one full collection per user per day** is feasible (e.g. on the order of **50,000–100,000 units/day** as a starting request, or as Google’s review process suggests). We can provide more detailed usage estimates or cap usage in software if required.

---

## 6. Compliance and safeguards

- **User-initiated:** All API calls occur only when a user runs the tool (CLI or web UI) and completes OAuth for their own channel.  
- **Own channel only:** OAuth scopes are limited to the minimum needed (upload, manage playlists); we do not access or upload to channels the user does not own.  
- **No bulk/automation abuse:** No scheduled or scripted bulk uploads across many channels; no reselling or proxy-upload service.  
- **Content:** Users choose archive.org URLs; the tool does not inject or suggest content. Responsibility for rights and YouTube policies remains with the creator.  
- **Open source:** The project is open source so that API usage and behavior can be reviewed.

---

## 7. Summary

| Item | Detail |
|------|--------|
| **API** | YouTube Data API v3 only |
| **Audience** | Creators (individuals/small orgs uploading to their own channels) |
| **Use case** | One-time or occasional upload of one archive.org collection (audio → videos + one playlist) per run |
| **Quota issue** | One 20-track run ≈ 34,000 units; default 10,000/day is insufficient for one full run |
| **Request** | Quota extension to allow at least one full collection per user per day (e.g. 50,000–100,000 units/day, or as advised by Google) |
| **Compliance** | User-initiated, OAuth, own channel only, no bulk/automated multi-channel uploads |

We are happy to provide additional technical details, usage statistics, or to implement rate limiting or reporting if required by the quota extension process.
