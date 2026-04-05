# Author Profiles & Favorite Authors — Changes Explanation

## 1. FavoriteAuthor Model

**What:** Added `FavoriteAuthor` model — a many-to-many relationship between users (follower → author).

**Where:** `backend/objects/models.py` (lines 260-272)

**Why:** To support the "favorite authors" feature, we need a database table that tracks which users follow which authors. Follows the same pattern as the existing `Favorite` model (user → cultural_object), with `unique_together` constraint to prevent duplicate follows.

---

## 2. UserProfileSerializer

**What:** Added `UserProfileSerializer` with fields: `username`, `date_joined`, `approved_objects_count`, `total_favorites_received`, `followers_count`, `is_followed`.

**Where:** `backend/objects/serializers.py` (lines 140-148)

**Why:** Needed a serializer for the public user profile API response. Uses `IntegerField(read_only=True)` for count fields instead of `SerializerMethodField` — the counts are computed via queryset annotations in the view, which is more efficient (single SQL query with JOINs instead of N+1 queries).

---

## 3. UserProfileViewSet

**What:** Added `UserProfileViewSet` with 4 actions:
- `retrieve` — GET `/api/users/<username>/` (public profile)
- `objects` — GET `/api/users/<username>/objects/` (author's objects)
- `follow` — POST `/api/users/<username>/follow/` (toggle follow)
- `favorite_authors` — GET `/api/users/favorite-authors/` (list followed authors)

**Where:** `backend/objects/views.py` (lines 656-771)

**Why:** Central endpoint for all author profile functionality. The `retrieve` action handles the "me" shortcut for authenticated users wanting their own profile. The `objects` action shows only approved objects to others but includes pending objects when viewing own profile. The `follow` action uses the same toggle pattern as object favorites (get_or_create → delete if exists). Self-follow is prevented with a validation check.

---

## 4. URL Registration

**What:** Registered `UserProfileViewSet` in the router as `'users'`.

**Where:** `backend/objects/urls.py` (line 8)

**Why:** DRF's DefaultRouter auto-generates URL patterns from registered viewsets. This creates all the `/api/users/` endpoints including detail actions (`/api/users/<username>/objects/`, `/api/users/<username>/follow/`) and list actions (`/api/users/favorite-authors/`).

---

## 5. Database Migration

**What:** Created and applied migration `0007_favoriteauthor.py`.

**Where:** `backend/objects/migrations/0007_favoriteauthor.py`

**Why:** The new `FavoriteAuthor` model requires a database table. The migration creates the table with the `unique_together` constraint on `(user, author)`.

---

## 6. AuthorProfile TypeScript Interface

**What:** Added `AuthorProfile` and `FollowToggleResponse` interfaces.

**Where:** `frontend/src/types/index.ts`

**Why:** Strict TypeScript typing for the new API responses. `AuthorProfile` maps to the `UserProfileSerializer` fields. `FollowToggleResponse` maps to the follow toggle endpoint response.

---

## 7. Users Service

**What:** Created `usersService` with 4 methods: `getProfile`, `getObjects`, `toggleFollow`, `getFavoriteAuthors`.

**Where:** `frontend/src/services/users.service.ts` (new file)

**Why:** Follows the existing service pattern (`objects.service.ts`) — each API resource gets its own service file. Centralizes all user/author API calls in one place.

---

## 8. AuthorProfilePage

**What:** Created a full author profile page with: info card (username, join date, stats, follow button), map with author's objects, and objects list.

**Where:** `frontend/src/pages/AuthorProfilePage.tsx` (new file)

**Why:** The main UI for viewing author profiles. Follows existing page patterns (`PopularPage`) for layout, loading/error states, and object list cards. Includes a map section using `MapContainer` + `MarkerClusterGroup` + `ObjectMarker` (same components as `MapView`). The follow button toggles state optimistically and shows "Ваш профіль" badge on own profile instead.

---

## 9. FavoriteAuthorsPage

**What:** Created a page listing authors the user follows, with unfollow buttons.

**Where:** `frontend/src/pages/FavoriteAuthorsPage.tsx` (new file)

**Why:** Users need a way to see and manage their author subscriptions. Removing an author from the list updates state immediately (optimistic UI). Follows the same layout pattern as other list pages.

---

## 10. Clickable Author Name on Detail Page

**What:** Changed the author name from plain text to a `<Link>` pointing to `/authors/<username>`.

**Where:** `frontend/src/pages/ObjectDetailPage.tsx` (line 244)

**Why:** This is the primary entry point to author profiles — users see an object's detail page and can click the author's name to view their profile. Styled with amber color to match the app's theme.

---

## 11. Routes

**What:** Added two routes: `/authors/:username` (public) and `/favorite-authors` (auth-protected).

**Where:** `frontend/src/App.tsx`

**Why:** The author profile page is public (anyone can view), while the favorite authors list requires authentication (it shows personal data — who the user follows).

---

## 12. Header Navigation Updates

**What:** Added "Підписки" nav link and made username clickable (links to own profile).

**Where:** `frontend/src/components/Layout/Header.tsx` (desktop + mobile nav)

**Why:** Users need quick access to their subscriptions list from the navigation. Making the username clickable provides a natural way to access one's own profile. Both desktop and mobile navigation were updated for consistency.
