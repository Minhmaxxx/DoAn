# Kế hoạch lưu trữ và khôi phục dữ liệu đa thiết bị

Phiên bản 3 — cập nhật 2026-08-18. Bản 1 chọn đúng database nhưng bỏ sót vấn đề
giữ phiên. Bản 2 giải quyết bằng `st.login()`. Bản 3 chốt phương án ma sát thấp
nhất: **ẩn danh trước, gắn tài khoản sau**.

## 1. Mục tiêu

Người dùng đăng nhập cùng một tài khoản trên điện thoại mới, máy tính hoặc sau
khi cài lại trình duyệt vẫn lấy lại được:

- Hồ sơ cá nhân và mục tiêu dinh dưỡng.
- Lịch sử các bữa ăn đã lưu.
- Các tổng hợp theo ngày và theo tuần.

`st.session_state` chỉ là cache giao diện. Nguồn dữ liệu chính phải là database
bên ngoài Streamlit, vì Streamlit có thể sleep, restart hoặc redeploy bất kỳ lúc
nào.

## 2. Vấn đề cốt lõi: giữ phiên

Chọn Supabase là đúng, nhưng chưa đủ. Trên Streamlit, `st.session_state` bị xóa
mỗi khi websocket đóng: người dùng F5, chuyển tab lâu, khóa màn hình điện thoại,
hoặc app redeploy. Nếu token chỉ nằm trong `st.session_state` thì người dùng bị
đăng xuất liên tục, và mục tiêu "đổi điện thoại vẫn dùng được" trở thành "đăng
nhập lại suốt".

Vậy bắt buộc phải có một **cookie trình duyệt**. Điều đã kiểm chứng trong
Streamlit 1.61.1:

- `st.context.cookies` chỉ **đọc** (`runtime/context.py:188`).
- Hàm ghi cookie duy nhất (`auth_util.set_cookie_with_chunks`) là nội bộ của
  `st.login()`, không phải API công khai.

Nên refresh token của Supabase phải được ghi bằng JavaScript vào
`document.cookie`, rồi đọc lại qua `st.context.cookies`. Codebase đã có sẵn
pattern JS trên parent document trong `utils/pwa.py`.

> **Đã sai và đã sửa (2026-08-19).** Vế "đọc lại qua `st.context.cookies`"
> **không dùng được trên Streamlit Community Cloud**: nền tảng không chuyển
> cookie của request tới app, nên `st.context.cookies` luôn rỗng khi deploy dù
> chạy tốt ở local. Đo thực tế trên production: trình duyệt có cookie, phía
> Python nhận về 0 cookie. Hệ quả là F5 mất phiên và đăng nhập Google hỏng.
>
> Cách làm hiện tại: `utils/cookies.py` bọc một Streamlit component
> (`extra-streamlit-components`) đọc `document.cookie` trong trình duyệt rồi
> trả giá trị qua **kênh component**, không đi qua HTTP header nên không bị
> nền tảng bóc. Hai điểm bắt buộc phải đúng: component cần **một vòng rerun**
> mới trả được cookie (phải phân biệt "chưa trả lời" với "không có cookie",
> nếu nhầm sẽ đăng xuất người dùng ở mỗi lần tải trang), và cookie phải đặt
> `SameSite=Lax` chứ không phải `Strict` mặc định của component — lượt quay về
> từ Google là điều hướng cross-site, đúng lúc `Strict` bị chặn.
>
> Bài học cho báo cáo: giả định rủi ro nhất của kế hoạch phải được kiểm chứng
> **trên đúng môi trường triển khai** trước khi xây tiếp. Local chạy tốt chính
> là thứ đã che giấu vấn đề này suốt cả Giai đoạn C.
>
> **Bổ sung 2026-08-20 — chiều ghi cũng hỏng, vì lý do khác.** Sau khi chiều
> đọc đã chạy (đo được 9 cookie qua component, 0 qua `st.context`), đo tiếp
> thấy `nv_refresh_token` không hề tồn tại sau khi bấm "Bật đồng bộ".
> Nguyên nhân: `manager.set()` chỉ *render một iframe*, cookie chỉ có thật khi
> JS trong iframe chạy — tức sau khi script kết thúc — còn `st.rerun()` ngay
> sau đó dựng lại cây phần tử trước khi kịp. Đây là nguyên nhân thật của "F5
> mất hồ sơ" và của các dòng `profiles` trùng tên (mỗi lần bật đồng bộ lại tạo
> một tài khoản ẩn danh mới vì lần trước không để lại cookie).
>
> `utils/cookies.py` nay xếp mọi lần ghi/xóa vào một hàng đợi trong session
> state và phát lại ở đầu mỗi vòng chạy cho tới khi trình duyệt xác nhận, nên
> chỗ gọi được phép `st.rerun()` thoải mái; đồng thời `read_cookie()` đọc
> overlay của chính mình trước snapshot của component, và xóa để lại tombstone
> để không khôi phục nhầm phiên vừa đăng xuất. Bài học nối tiếp: bảng chẩn
> đoán phải đo **cả hai chiều** — đọc được cookie *và* ghi có tới nơi.

Hệ quả bảo mật phải chấp nhận: cookie ghi bằng JS **không thể đặt HttpOnly**.
Đây là cách hoạt động tiêu chuẩn của mọi app dùng supabase-js (mặc định còn lưu
localStorage, kém an toàn hơn), nhưng nó nâng mức nghiêm trọng của bất kỳ lỗ XSS
nào lên thành chiếm tài khoản. Xem mục 9.

## 3. Kiến trúc chốt: ẩn danh trước, gắn tài khoản sau

Toàn bộ danh tính và dữ liệu do Supabase quản lý. Không dùng `st.login()`.

**Bước 1 — Ẩn danh, tạo lười.** Người dùng mới không phải làm gì cả: không đăng
ký, không mật khẩu, không gõ mã. Lần **đầu tiên họ lưu dữ liệu** (lưu hồ sơ hoặc
lưu bữa ăn), app gọi `sign_in_anonymously()`, tạo một dòng thật trong
`auth.users` và từ đó dữ liệu được đồng bộ.

Tạo lười chứ không tạo ngay khi mở trang, vì hai lý do: khách vãng lai và bot
không sinh rác trong `auth.users`, và số MAU tính phí không bị thổi lên.

**Bước 2 — Gắn Google khi cần đa thiết bị.** Chỉ khi người dùng muốn dùng máy
khác, họ bấm "Liên kết tài khoản Google". Dùng `link_identity()` với luồng PKCE:
app chuyển hướng sang Supabase, Supabase lo Google, rồi quay lại app kèm `?code=`
đọc được bằng `st.query_params`, và `exchange_code_for_session(code)` hoàn tất.

Điểm mấu chốt: `link_identity()` giữ **nguyên `auth.users.id` cũ**. Không phải
di trú dữ liệu, không phải viết RPC `security definer` để chuyển chủ sở hữu, và
không có khoảnh khắc nào dữ liệu mồ côi.

Sang thiết bị mới: đăng nhập Google, nhận đúng `user_id` cũ, dữ liệu hiện lại.

**Kết quả:** `auth.uid()` hoạt động bình thường trong mọi trường hợp, nên
`storage_schema.sql` **không cần sửa một dòng nào**, kể cả khóa ngoại
`references auth.users(id)` và toàn bộ policy RLS.

### Vì sao không chọn hai phương án còn lại

**Mã đồng bộ tự phát (mỗi user một key bí mật).** Ma sát ban đầu tưởng thấp
nhưng thực tế cao hơn ẩn danh: người dùng phải cất giữ một chuỗi ký tự, và sang
máy mới phải gõ lại 32 ký tự trên bàn phím điện thoại. Ba cái giá: mất key là
mất sạch không có đường khôi phục; lộ key là chiếm tài khoản vĩnh viễn và im
lặng; và vì không có `auth.uid()` nên phải hoặc dùng `service_role` (bỏ RLS) hoặc
tự ký JWT kèm bỏ khóa ngoại tới `auth.users`. Ẩn danh cho ma sát bằng 0 mà không
phải trả giá nào trong ba cái đó.

**Email/mật khẩu qua Supabase Auth.** SMTP mặc định của free tier giới hạn vài
email mỗi giờ, nên xác minh email và đặt lại mật khẩu rất dễ fail đúng lúc bảo
vệ đồ án. Có thể bổ sung sau như provider thứ hai.

### Những quyết định giữ nguyên từ bản 1

- UUID `auth.users.id` là `user_id` ổn định cho mỗi tài khoản.
- API key OpenAI/Gemini không bao giờ là `user_id` và không lưu plaintext trong
  database. Key vẫn nằm trong session, hoặc dùng key chung của chủ dự án trong
  Streamlit Secrets.
- Chưa lưu ảnh món ăn. App chỉ cần kết quả nhận diện; không lưu ảnh thì giảm chi
  phí và rủi ro riêng tư. Nếu sau này cần, dùng Supabase Storage private bucket
  với path bắt đầu bằng `user_id`.

## 4. Ba trạng thái của người dùng

| Trạng thái | Dữ liệu | Đa thiết bị |
|---|---|---|
| Khách (chưa lưu gì) | Chỉ trong session | Không |
| Ẩn danh (đã lưu ít nhất một lần) | Supabase, gắn cookie thiết bị | Không — mất thiết bị là mất dữ liệu |
| Đã liên kết Google | Supabase | Có |

Mỗi trang phải hiển thị rõ đang ở trạng thái nào. Nhãn `LƯU TRONG PHIÊN` ở
`pages/3_Ho_so.py` và caption ở landing/`utils/navigation.py` phải đổi theo, và
tuyệt đối không nói "đã đồng bộ" khi mới ở mức ẩn danh.

Trạng thái ẩn danh phải kèm một lời nhắc thành thật, không phô trương: dữ liệu
đã được lưu trên máy chủ nhưng chỉ thiết bị này mở được, liên kết Google để dùng
trên máy khác.

Chế độ khách còn một tác dụng kỹ thuật: toàn bộ `tests/test_pages.py` chạy ở chế
độ đó, nên release gate không cần mạng.

## 5. Mô hình dữ liệu và ánh xạ

Schema giữ nguyên `storage_schema.sql`:

- `profiles`: một dòng cho mỗi `user_id`.
- `meals`: `id`, `user_id`, `eaten_at timestamptz`, `meal_type`, `foods jsonb`,
  `totals jsonb`, index `(user_id, eaten_at desc)`.

Hai chi tiết ánh xạ dễ gây lỗi, phải làm đúng ngay từ đầu:

**Múi giờ.** Bản ghi trong session có `date` và `time` là chuỗi theo giờ Việt
Nam, còn database lưu `eaten_at` dạng `timestamptz`. Khi tải về **bắt buộc** đi
qua `utils.history.as_vietnam_time()` rồi mới sinh lại `date`/`time`. Nếu format
thẳng từ UTC thì bộ lọc `meal.get("date") == today` ở `pages/0_Hom_nay.py:40` sẽ
sai lệch 7 tiếng và trang "Hôm nay" mất bữa ăn buổi tối. Thêm hàm
`record_from_row()` vào `utils/history.py` để chỉ có một chỗ làm việc này.

**Chống ghi trùng.** `meals.id` sinh phía client bằng
`uuid5(NAMESPACE_URL, f"{user_id}:{meal_signature}")` thay vì để database tự
sinh. `meal_signature` đã tồn tại ở `pages/1_Phan_tich_anh.py`, nên khi mạng
chập chờn và người dùng bấm lưu lại, insert thứ hai va vào primary key và bị bỏ
qua thay vì tạo bữa ăn trùng. Cơ chế `saved_meal_signatures` trong session vẫn
giữ để phản hồi UI nhanh.

**Ràng buộc CHECK.** Các cột `gender`, `activity_level`, `goal` trong schema
liệt kê đúng từng chuỗi tiếng Việt đang dùng làm khóa tra cứu ở
`utils/nutrition.py`. Đây là chốt chặn thứ hai cho hợp đồng dữ liệu: sửa một
nhãn ở trang hồ sơ mà quên sửa nơi khác thì insert sẽ fail. Khi thay đổi các
chuỗi này phải cập nhật đồng thời `utils/nutrition.py`, `pages/3_Ho_so.py`,
`utils/state.py` và `storage_schema.sql`.

`profiles` không có cột `profile_completed`. Trạng thái đó suy ra từ việc dòng
profile có tồn tại hay không.

## 6. Thiết kế module

Hai module mới, đều thuần logic để test được không cần mạng:

**`utils/auth.py`** (tên hàm thật, đã cài đặt ở Giai đoạn B — khác vài chỗ so
với bản nháp đầu tiên của mục này):
- `current_user_id()` / `is_linked()` — trả về `user_id`, trạng thái ẩn danh
  hay đã liên kết
- `ensure_account(client)` — tạo lười tài khoản ẩn danh, gọi ngay trước lần
  ghi đầu
- `start_google_link(client, redirect_to)` / `complete_oauth_callback(client,
  auth_code)` — luồng PKCE qua `st.query_params`
- `restore_session(client)` — đọc refresh token qua `utils/cookies.py` và
  khôi phục
- `persist_session()` / `clear_session_cookie()` — ghi và xóa cookie qua
  `utils/cookies.py` (hàng đợi có retry, xem ghi chú 2026-08-20 ở mục 2)
- `logout(client)` — xóa cookie, session Supabase, `user_profile`,
  `meal_history`, `llm_runtime_config`, `_supabase_client` và các key API tạm
- `get_client()` — dựng **một lần** `supabase.Client` và cache trong
  `st.session_state["_supabase_client"]` cho cả phiên; **không** dựng mới mỗi
  lần gọi (xem "Xác nhận từ spike Giai đoạn 0" ngay dưới, đây là lỗi thiết kế
  ban đầu đã sửa, không phải chỉ tối ưu tốc độ)

Lưu ý contract quan trọng: `get_client()` trả về `Client` (cấp cao nhất, có
`.table(...)`) — mọi hàm còn lại trong `utils/auth.py` (`ensure_account`,
`restore_session`, `start_google_link`, `complete_oauth_callback`, `logout`)
nhận `client.auth` (sub-client), không phải `client`. `utils/repository.py`
thì ngược lại, nhận thẳng `client` cấp cao nhất. Trang gọi cả hai module phải
tự phân biệt hai tham số này.

**`utils/repository.py`** — interface hẹp, không page nào gọi thẳng Supabase:
- `load_profile()` / `save_profile(profile)` (upsert)
- `load_meals(limit=50)` / `save_meal(meal_data, signature)` /
  `delete_all_meals()`
- `SessionRepository` (chế độ khách) và `SupabaseRepository(client, user_id)`
  cùng implement interface đó.

Các trang gọi `get_repository()` và không cần biết mình đang ở trạng thái nào.
Đây cũng là cách giữ test: tiêm `SessionRepository` hoặc một fake in-memory, nên
release gate không có lời gọi mạng nào.

### Xác nhận từ spike Giai đoạn 0 (chạy thật trên project, 2026-08-19)

Bốn điểm sau **sai trong giả định ban đầu**, phát hiện được chính là lý do
Giai đoạn 0 tồn tại như một bước riêng trước khi nối vào trang:

1. **`link_identity()` cần `redirect_to` lồng trong `options`**, không phải
   khóa cấp cao nhất — `{"provider": "google", "options": {"redirect_to":
   ...}}`. Đặt sai vị trí không báo lỗi, chỉ âm thầm bỏ qua `redirect_to`.
2. **`get_client()` phải cache `Client`, không được dựng mới mỗi lần gọi.**
   Supabase-py chỉ gắn JWT của người dùng vào header Postgrest thông qua một
   listener sự kiện sign-in/refresh **trên chính object `Client` đó**. Một
   `Client` mới ở mỗi lần gọi nghĩa là mọi truy vấn của `SupabaseRepository`
   luôn chạy bằng anon key, và RLS sẽ chặn hết — lỗi này sẽ không lộ ra ở unit
   test (vì test luôn tiêm fake client), chỉ lộ khi chạy thật.
3. **PKCE `code_verifier` cần một storage backend riêng ngoài bộ nhớ mặc
   định.** `link_identity()` tự sinh `code_verifier` và lưu vào bộ nhớ trong
   của `Client`; nhưng redirect sang Google rồi quay lại là một lượt tải
   trang hoàn toàn mới trong Streamlit (`st.session_state` không sống sót qua
   đó), nên `Client` dựng lại ở lượt callback không còn thấy `code_verifier`
   cũ → `exchange_code_for_session()` thất bại. Đã vá bằng
   `_CodeVerifierCookieStorage` (cookie riêng, khác cookie refresh-token,
   TTL 10 phút) gắn qua `SyncClientOptions(persist_session=False,
   storage=...)` — `persist_session=False` vì module đã tự quản lý cookie
   refresh-token riêng, không cần supabase-py làm lại việc đó.
4. **`maybe_single().execute()` trả về `None` thẳng khi không có dòng nào**,
   không phải một response object với `.data=None`. `SupabaseRepository.
   load_profile()` ban đầu giả định sai điều này; đã sửa thành
   `result.data if result else None`.

Đã xác minh bằng ghi/đọc/xóa thật (profile + meal) trên project thật qua RLS,
không chỉ đọc mã nguồn SDK. Chi tiết đầy đủ: `PROGRESS.md`, mục ngày
2026-08-19.

Điểm nối vào code hiện có:

| Vị trí | Thay đổi |
|---|---|
| `utils/state.py` | Thêm key `auth_user`, `sync_status`; giữ nguyên các default cũ |
| `pages/3_Ho_so.py` sau `submitted` | `ensure_account()` rồi `repo.save_profile()`; chỉ báo "Đã lưu hồ sơ" khi server xác nhận |
| `pages/3_Ho_so.py` mục mới | Nút liên kết Google và trạng thái đồng bộ |
| `pages/1_Phan_tich_anh.py` `_save_to_history` | `ensure_account()` rồi `repo.save_meal()`, thêm vào session sau |
| `pages/2_Lich_su.py` `load_all_history` | `repo.load_meals()` |
| `pages/2_Lich_su.py` nút "Xóa tất cả" | `repo.delete_all_meals()`, xác nhận hai bước |
| `pages/0_Hom_nay.py` | Không đổi logic, chỉ đọc từ cache đã nạp |
| `utils/navigation.py` | Thêm chỉ báo trạng thái đồng bộ vào app shell |
| `app.py` | Gọi `restore_session()` và `handle_oauth_callback()` sớm |

## 7. Luồng đồng bộ

- Mở app: `restore_session()` đọc cookie; nếu có thì tải profile và tối đa 50
  bữa ăn gần nhất vào session làm cache.
- Lưu hồ sơ: upsert `profiles`, rồi mới cập nhật session.
- Lưu bữa ăn: insert `meals`, chỉ thêm vào session sau khi database thành công.
- Xóa lịch sử: xác nhận hai bước, xóa theo `user_id` hiện tại.
- Đăng xuất: xóa cookie và mọi dữ liệu cá nhân khỏi session.
- Mất mạng: báo lỗi rõ ràng và **không** hiển thị "Đã lưu" nếu server chưa nhận.

Nếu người dùng đã có dữ liệu ẩn danh trên máy này rồi đăng nhập Google bằng một
tài khoản **đã có dữ liệu khác**, `link_identity()` sẽ báo lỗi identity đã tồn
tại. Khi đó phải hỏi người dùng chọn giữ bộ nào, không tự động trộn.

## 8. Cấu hình, bí mật và chi phí

Trong Streamlit Secrets của app production:

```toml
[supabase]
url = "https://<project>.supabase.co"
publishable_key = "<anon/publishable key>"
```

Trong Supabase Dashboard:

- Auth → Providers → **Anonymous sign-ins**: bật (mặc định tắt).
- Auth → Providers → **Google**: dán client ID và client secret lấy từ Google
  Cloud Console; callback URL do Supabase cung cấp.
- Auth → **Manual Linking** (`security_manual_linking_enabled`): **bật**. Mặc
  định tắt, và khi tắt thì `link_identity()` trả lỗi `Manual linking is
  disabled` — nút "Liên kết Google" hỏng đúng ở bước cuối. Phát hiện khi test
  thật trên trình duyệt ngày 2026-08-19, không lộ ra ở bất kỳ bài test tự động
  nào vì luồng này cần một phiên đăng nhập thật.
- Auth → URL Configuration: Site URL và Redirect URL trỏ về
  `https://nutrivisionnn.streamlit.app`. Muốn test ở máy local thì thêm
  `http://localhost:8501` vào **Redirect URLs** và đặt `site_url` trong
  `.streamlit/secrets.toml`; thiếu bước này Google sẽ trả người dùng về bản
  production thay vì app đang chạy trên máy.

Trong Google Cloud Console: tạo một OAuth 2.0 Client ID loại Web application,
authorized redirect URI là callback của Supabase. Cần thêm một client riêng cho
`http://localhost:8501` để phát triển không phải deploy.

Dependency phải thêm vào `requirements.txt` (runtime, vì đó là file Streamlit
Cloud cài): `supabase>=2.0`. Hiện chưa được cài.

Tuyệt đối không đưa `service_role` key vào app hay GitHub. Nếu dùng key đó thì
RLS bị bỏ qua và một lỗi lập trình là đủ để lộ dữ liệu người khác.

**Chi phí: $0.** Supabase free tier (500MB database, 50k MAU) không cần thẻ. Tạo
OAuth client trên Google Cloud Console miễn phí và không cần bật billing —
"Sign in with Google" không nằm trong hệ thống tính phí của GCP. Không dùng AWS
cho phần này: credit có hạn sử dụng và tài khoản đã áp thẻ sẽ bị tính tiền thật
khi hết credit, trong khi phải viết lại toàn bộ Cognito và bỏ `storage_schema.sql`
để đổi lấy quá ít.

**Chống pause.** Supabase free pause project sau 7 ngày không hoạt động, và đồ án
thường nằm im giữa các buổi demo. Thêm một GitHub Actions cron hàng tuần chạy một
truy vấn nhẹ để giữ project sống; repo đã có sẵn `.github/workflows/`. Vẫn phải
kiểm tra và đánh thức trước buổi bảo vệ, không tin tuyệt đối vào cron.

## 9. Hardening bắt buộc

Vì refresh token nằm trong cookie đọc được bằng JS, một lỗ XSS sẽ thành chiếm
tài khoản. Hiện trạng đã kiểm tra: `utils/ui.py` bọc `html.escape()` cho mọi
tham số, và tên hồ sơ đi qua `render_page_header()` nên **hiện không có lỗ**.

Việc phải làm:

- Rà toàn bộ 23 chỗ dùng `unsafe_allow_html=True` trong `pages/` và `app.py`,
  xác nhận không chỗ nào nội suy thẳng dữ liệu người dùng vào HTML.
- Thêm test chốt hành vi này: lưu hồ sơ có tên chứa `<script>` và khẳng định
  chuỗi thoát xuất hiện trong output, không phải thẻ thật.
- Cookie đặt `Secure` và `SameSite=Lax`, thời hạn hữu hạn.

## 10. Ảnh hưởng đến release gate

- Sáu bài render trong `tests/test_pages.py` phải vẫn pass ở chế độ khách. Đây
  là tiêu chí chấp nhận, không phải điều chỉnh test cho vừa code.
- `test_profile_is_completed_only_after_form_submission` và
  `test_history_clear_only_changes_active_session` mô tả hành vi chế độ khách —
  giữ nguyên.
- Test mới, tất cả offline: ánh xạ record ↔ row khứ hồi đúng kể cả múi giờ;
  `uuid5` ổn định cho cùng `meal_signature`; `SessionRepository` đúng hợp đồng
  interface; `logout()` xóa sạch mọi key nhạy cảm; escaping ở mục 9.
- Kiểm thử RLS và đa thiết bị là thủ công, không đưa vào CI vì cần mạng và
  credentials.

## 11. Lộ trình

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 0 | Spike: dựng Supabase project, bật anonymous sign-in, xác nhận `sign_in_anonymously` rồi `link_identity` giữ nguyên `user_id` | **Xong 2026-08-19** — xem "Xác nhận từ spike Giai đoạn 0" ở mục 6 |
| A | Hạ tầng: chạy `storage_schema.sql`, tạo OAuth client cho local và production, khai báo secrets, cron chống pause | **Phần lớn xong 2026-08-19** — project, schema, Anonymous, Google provider đều đã bật và xác minh bằng ghi/đọc thật; cron chống pause 7 ngày còn thiếu |
| B | `utils/auth.py`, `utils/repository.py`, `record_from_row()`, test offline | Xong (trước 2026-08-19), đã vá lại theo phát hiện của Giai đoạn 0 |
| C | Nối vào 4 trang, chỉ báo trạng thái, nút liên kết Google | **Xong 2026-08-19** — xem "Thay đổi ở Giai đoạn C" bên dưới |
| D | Hardening mục 9, export JSON dự phòng | Chưa bắt đầu |
| E | Ma trận kiểm thử mục 12, cập nhật `README.md` và `PROGRESS.md` | Chưa bắt đầu |

Giai đoạn 0 xác nhận đúng giả định quan trọng nhất của kế hoạch — liên kết
Google không làm đổi `user_id` — nhưng cũng lật ra 4 chỗ sai khác trong
`utils/auth.py`/`utils/repository.py` mà chỉ chạy thật mới thấy (liệt kê đầy
đủ ở mục 6). Đây chính xác là lý do giữ Giai đoạn 0 tách riêng khỏi Giai đoạn
C thay vì gộp chung.

### Thay đổi ở Giai đoạn C so với thiết kế ban đầu

**Đồng bộ là opt-in, không tự bật khi lưu lần đầu.** Mục 6 ban đầu ghi
"`pages/3_Ho_so.py` sau `submitted` → `ensure_account()` rồi
`repo.save_profile()`", tức mọi lần lưu hồ sơ đầu tiên đều âm thầm tạo tài
khoản trên máy chủ. Đã đổi thành một nút **"Bật đồng bộ"** tường minh
(`utils.repository.enable_sync()`), vì hai lý do:

1. Đẩy hồ sơ sức khỏe của người dùng lên máy chủ ngay khi họ bấm "Lưu thay
   đổi", chưa từng hỏi, không phải quyết định nên làm ngầm.
2. Nó giữ chế độ khách làm mặc định **thật sự**, nên `tests/test_pages.py`
   offline theo cấu trúc chứ không nhờ mock. Máy dev đã có `secrets.toml`
   thật, nếu tự bật thì mỗi lần chạy AppTest trang hồ sơ sẽ tạo một tài khoản
   ẩn danh sống trong `auth.users`.

Tính chất "tạo lười" ở mục 3 không đổi: khách không bật thì không sinh dòng
nào trong `auth.users`. Khi bật, `enable_sync()` đẩy hồ sơ và toàn bộ lịch sử
đang có trong phiên lên trước rồi mới đọc lại, nên không mất dữ liệu đã nhập.

**Hai lỗi phát hiện khi chạy thật ở Giai đoạn C** (unit test dùng fake không
bắt được, giống hệt bài học của Giai đoạn 0):

3. **Không được khóa bản ghi bữa ăn theo `timestamp`.** `datetime.now()` trên
   Windows chỉ phân giải ~16ms, đã đo thực tế: năm bản ghi tạo liên tiếp có
   timestamp **giống hệt nhau**. Bản đầu của `record_signature()` lấy
   timestamp làm khóa, khiến hai bữa ăn khác nhau đè lên nhau thành một dòng
   khi di trú lên cloud — mất dữ liệu thật sự, không phải chỉ lỗi hiển thị.
   Đã đổi sang hash SHA-256 của nội dung bản ghi.
4. **`st.context.cookies.get()` trả về `MagicMock` dưới AppTest** — luôn
   truthy. `bootstrap_session()` vì thế tưởng có refresh token, dựng client và
   (trên máy dev có secrets thật) sẽ gọi mạng để refresh bằng một mock object,
   phá vỡ cam kết release gate không chạm mạng. Đã sửa: cookie chỉ được chấp
   nhận khi là `str` không rỗng. `tests/test_pages.py` có bài chốt cả sáu
   trang không dựng client ở chế độ khách.

## 12. Ma trận kiểm thử bắt buộc

1. Tài khoản A không đọc/sửa/xóa được dữ liệu tài khoản B — thử trực tiếp bằng
   PostgREST với JWT của A, không chỉ thử qua UI.
2. **F5 giữa chừng vẫn giữ nguyên danh tính** — bài test cho vấn đề ở mục 2.
3. Mở app từ icon PWA sau khi đóng trình duyệt vẫn giữ dữ liệu.
4. Ẩn danh trên máy A, liên kết Google, đăng nhập trên máy B: thấy đủ dữ liệu cũ
   và `user_id` không đổi.
5. Redeploy Streamlit không làm mất dữ liệu và không làm mất phiên.
6. Token hết hạn được refresh, hoặc yêu cầu đăng nhập lại một cách rõ ràng.
7. Xóa tài khoản xóa cả profile và meals theo `ON DELETE CASCADE`.
8. Chế độ khách vẫn hoạt động đầy đủ khi chưa lưu gì.
9. Mở app rồi thoát mà không lưu gì: **không** sinh dòng nào trong `auth.users`.
10. Lưu bữa ăn khi mất mạng: báo lỗi, không hiện "Đã lưu", không tạo bản ghi ma.
11. Bấm lưu hai lần liên tiếp chỉ tạo một dòng trong `meals`.
12. Liên kết Google bằng tài khoản đã có dữ liệu khác: báo lỗi rõ ràng, không
    trộn dữ liệu, không mất bên nào.
13. Đăng nhập trên iPhone ở chế độ PWA standalone: redirect OAuth quay lại đúng
    app. Đây là điểm rủi ro nhất về trải nghiệm, phải thử trên máy thật.
14. Project Supabase sau khi bị pause và restore: dữ liệu còn nguyên.

## 13. Rủi ro và phương án dự phòng

| Rủi ro | Xử lý |
|---|---|
| `link_identity` không giữ `user_id` như kỳ vọng | Giai đoạn 0 phát hiện sớm. Dự phòng: RPC `security definer` chuyển chủ sở hữu từ user ẩn danh sang user Google, chạy trong một transaction |
| OAuth redirect hỏng trong PWA standalone trên iOS | Ưu tiên mở link đăng nhập ở tab thường; nếu vẫn hỏng, ghi rõ trong báo cáo là giới hạn đã biết |
| Bot tạo hàng loạt user ẩn danh | Tạo lười ở mục 3 đã giảm phần lớn; nếu vẫn bị, bật CAPTCHA cho anonymous sign-in trong Supabase |
| Người dùng ẩn danh mất thiết bị | Đã chấp nhận có ý thức. Bù lại bằng lời nhắc ở mục 4 và nút export JSON ở giai đoạn D |
| Supabase free pause | Cron hàng tuần ở mục 8, cộng với kiểm tra thủ công trước buổi bảo vệ |

## 14. Giới hạn hiện tại

Trước khi giai đoạn A–C hoàn tất, dữ liệu vẫn chỉ nằm trong session và không thể
khôi phục nếu người dùng mất thiết bị hoặc hết session. Không thông báo với người
dùng rằng dữ liệu đã đồng bộ cho tới khi pass toàn bộ ma trận ở mục 12 — đặc biệt
là các bài 1, 2, 4 và 5.
