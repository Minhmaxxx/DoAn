# Kế hoạch lưu trữ và khôi phục dữ liệu đa thiết bị

## 1. Mục tiêu

Người dùng đăng nhập cùng một tài khoản trên điện thoại mới, máy tính hoặc sau
khi cài lại trình duyệt vẫn lấy lại được:

- Hồ sơ cá nhân và mục tiêu dinh dưỡng.
- Lịch sử các bữa ăn đã lưu.
- Các tổng hợp theo ngày và theo tuần.

`st.session_state` chỉ là cache giao diện. Nguồn dữ liệu chính phải là database
bên ngoài Streamlit, vì Streamlit có thể sleep, restart hoặc redeploy bất kỳ lúc
nào.

## 2. Quyết định kiến trúc

Sử dụng:

- Supabase Auth để đăng ký, đăng nhập, xác minh email và khôi phục mật khẩu.
- Supabase PostgreSQL để lưu hồ sơ và bữa ăn.
- UUID `auth.users.id` làm `user_id` ổn định cho mỗi tài khoản.
- Row Level Security (RLS) để mỗi tài khoản chỉ đọc/ghi dữ liệu của chính mình.

Không tạo một static secret key riêng để người dùng ghi nhớ. Key bí mật không
thay thế được tài khoản: mất key sẽ mất quyền truy cập, lộ key sẽ lộ dữ liệu và
khó khôi phục. Trên thiết bị mới, người dùng chỉ cần đăng nhập lại bằng cùng
email; nếu quên mật khẩu thì dùng email khôi phục của Supabase.

API key OpenAI/Gemini không được dùng làm `user_id`. Ban đầu tiếp tục giữ key đó
trong session hoặc dùng key chung của chủ dự án trong Streamlit Secrets. Không
lưu API key người dùng dạng plaintext trong database.

## 3. Mô hình dữ liệu

Schema có thể tạo trước nằm trong `storage_schema.sql`:

- `profiles`: một dòng cho mỗi `user_id`.
- `meals`: một dòng cho mỗi bữa ăn, có `user_id`, thời điểm, danh sách món và
  tổng dinh dưỡng.
- Index `(user_id, eaten_at)` để tải lịch sử của một người theo thời gian.
- Mọi lệnh select/insert/update/delete đều bị RLS ràng buộc theo `auth.uid()`.

Không lưu ảnh món ăn ở giai đoạn đầu. App hiện chỉ cần kết quả nhận diện, vì vậy
không lưu ảnh sẽ giảm chi phí và rủi ro riêng tư. Nếu sau này cần ảnh, dùng
Supabase Storage private bucket với path bắt đầu bằng `user_id` và policy riêng.

## 4. Luồng khôi phục trên điện thoại mới

1. Người dùng mở NutriVision trên thiết bị mới.
2. Đăng nhập bằng email và mật khẩu đã đăng ký.
3. Supabase Auth trả về session có JWT và `user_id` cũ.
4. App truy vấn `profiles` và `meals` bằng JWT của người dùng.
5. RLS chỉ trả về các dòng có `user_id` trùng tài khoản.
6. App nạp dữ liệu vào `st.session_state` để hiển thị nhanh.

Nếu người dùng quên mật khẩu, nút "Quên mật khẩu" gửi link đặt lại mật khẩu tới
email đã xác minh. Vì dữ liệu gắn với `user_id` trên server, đổi điện thoại không
làm đổi chủ sở hữu dữ liệu.

## 5. Luồng đồng bộ trong ứng dụng

- Sau đăng nhập: tải profile và tối đa 50 bữa ăn gần nhất.
- Lưu hồ sơ: `upsert` vào `profiles`, sau đó cập nhật cache session.
- Lưu bữa ăn: insert vào `meals`, chỉ thêm vào session sau khi database thành
  công.
- Xóa lịch sử: xác nhận hai bước, delete các bữa ăn của `user_id` hiện tại.
- Đăng xuất: xóa JWT, profile, history và API key tạm khỏi `st.session_state`.
- Mất mạng: báo lỗi và không hiển thị thông báo "Đã lưu" nếu server chưa nhận.

Mỗi meal cần UUID để việc retry không tạo bản ghi trùng. Khi đăng nhập lần đầu,
nếu session ẩn danh đang có dữ liệu, app phải hỏi người dùng có muốn nhập dữ liệu
tạm vào tài khoản hay không; không tự động trộn dữ liệu.

## 6. Thứ tự triển khai

### Giai đoạn A - Hạ tầng

1. Tạo Supabase project gần khu vực người dùng nếu gói dịch vụ cho phép.
2. Chạy `storage_schema.sql` trong Supabase SQL Editor.
3. Bật email/password Auth và xác minh email.
4. Đặt Site URL và redirect URL thành URL Streamlit production.
5. Lưu `SUPABASE_URL` và `SUPABASE_PUBLISHABLE_KEY` trong Streamlit Secrets.
6. Tuyệt đối không đưa secret key/service-role key vào app hoặc GitHub.

### Giai đoạn B - Tích hợp code

1. Thêm Supabase Python client vào dependency runtime.
2. Thêm module auth: sign up, sign in, sign out, reset password và refresh
   session.
3. Thêm module repository để load/save profile và meals.
4. Chặn các trang cá nhân khi chưa đăng nhập.
5. Chuyển `st.session_state` thành cache, không còn là nơi lưu duy nhất.
6. Thêm import dữ liệu session ẩn danh và export JSON dự phòng.

### Giai đoạn C - Kiểm thử bắt buộc

1. Tài khoản A không đọc/sửa/xóa được dữ liệu tài khoản B.
2. Đăng nhập A trên trình duyệt khác vẫn thấy đủ profile và history.
3. Quên mật khẩu và đặt lại mật khẩu không làm mất dữ liệu.
4. Redeploy Streamlit không làm mất dữ liệu.
5. Token hết hạn được refresh hoặc yêu cầu đăng nhập lại rõ ràng.
6. Xóa tài khoản xóa profile và meals theo `ON DELETE CASCADE`.

## 7. Giới hạn hiện tại

Trước khi Giai đoạn A và B hoàn tất, dữ liệu vẫn chỉ nằm trong session và không
thể khôi phục nếu người dùng mất thiết bị/hết session. Không nên thông báo với
người dùng rằng dữ liệu đã đồng bộ cho tới khi đã pass các test đa thiết bị và
RLS ở Giai đoạn C.
