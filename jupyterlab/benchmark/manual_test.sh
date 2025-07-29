#!/bin/bash

# --- Konfigurasi ---
JUPYTERHUB_URL="http://10.33.17.30:18000" # Ganti dengan URL JupyterHub kamu
USERNAME="testuser1"                     # Ganti dengan username kamu
PASSWORD="testuser1"                     # Ganti dengan password kamu
KERNEL_SPEC_NAME="python3-docker-rpl"  # Ganti dengan nama kernel spec yang ingin diluncurkan
# ASUMSI: Profil dan node selection seperti di mass.py sudah diatur secara eksternal atau default
# Misalnya, profil default adalah 'single-cpu' dan image 'danielcristh0/jupyterlab:cpu'
PROFILE_ID="single-cpu"                 # Ganti dengan ID profil yang sesuai di JupyterHub kamu
PROFILE_NAME="single-cpu"
IMAGE_NAME="danielcristh0/jupyterlab:cpu"
PRIMARY_NODE="rpl-02" # Ini adalah contoh. Kamu perlu tahu hostname node target atau ambil dari Discovery API

# Direktori untuk menyimpan file sementara
TEMP_DIR="./tmp"
mkdir -p "$TEMP_DIR"

COOKIE_FILE="$TEMP_DIR/jupyterhub_cookies.txt"
XSRF_TOKEN_FILE="$TEMP_DIR/xsrf_token.txt"
KERNEL_ID_FILE="$TEMP_DIR/kernel_id.txt"

echo "=== Memulai Proses Login dan Launch Kernel ==="

# 1. Mengambil XSRF Token dari halaman login
echo "1. Mengambil XSRF token dari halaman login..."
LOGIN_PAGE_HTML=$(curl -s -L -c "$COOKIE_FILE" "$JUPYTERHUB_URL/hub/login")
XSRF_TOKEN=$(echo "$LOGIN_PAGE_HTML" | sed -n 's/.*name="_xsrf" value="\([^"]*\)".*/\1/p' | head -n 1)

if [ -z "$XSRF_TOKEN" ]; then
    echo "ERROR: Gagal mendapatkan XSRF token dari halaman login. Exit."
    rm -f "$COOKIE_FILE" "$XSRF_TOKEN_FILE"
    exit 1
fi
echo "$XSRF_TOKEN" > "$XSRF_TOKEN_FILE"
echo "   XSRF Token berhasil didapatkan: $XSRF_TOKEN"

# 2. Melakukan POST login ke JupyterHub
echo "2. Melakukan login ke JupyterHub sebagai $USERNAME..."
LOGIN_POST_RESPONSE=$(curl -s -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD" \
    --data-urlencode "_xsrf=$XSRF_TOKEN" \
    "$JUPYTERHUB_URL/hub/login" \
    -D "$TEMP_DIR/login_header.txt")

LOGIN_STATUS_CODE=$(grep HTTP/1.1 "$TEMP_DIR/login_header.txt" | awk '{print $2}' | tail -n 1)

if [[ "$LOGIN_STATUS_CODE" == "302" || "$LOGIN_STATUS_CODE" == "303" ]]; then
    echo "   Login berhasil (status $LOGIN_STATUS_CODE, kemungkinan redirect)."
else
    echo "ERROR: Login gagal (status $LOGIN_STATUS_CODE)."
    echo "Respons penuh:"
    echo "$LOGIN_POST_RESPONSE"
    rm -f "$COOKIE_FILE" "$XSRF_TOKEN_FILE"
    exit 1
fi

# 3. Mengambil XSRF token baru dari halaman /hub/home (setelah login)
# Ini penting karena token bisa berubah setelah otentikasi
echo "3. Mengambil XSRF token baru setelah login dari /hub/home..."
HOME_PAGE_HTML=$(curl -s -L -b "$COOKIE_FILE" -c "$COOKIE_FILE" "$JUPYTERHUB_URL/hub/home")
NEW_XSRF_TOKEN=$(echo "$HOME_PAGE_HTML" | sed -n 's/.*name="_xsrf" value="\([^"]*\)".*/\1/p' | head -n 1)

if [ -z "$NEW_XSRF_TOKEN" ]; then
    NEW_XSRF_TOKEN=$(echo "$HOME_PAGE_HTML" | grep -oP 'window.jhdata = {[^}]*xsrf_token: "\K[^"]+')
    if [ -z "$NEW_XSRF_TOKEN" ]; then
        echo "WARNING: XSRF token baru tidak ditemukan di halaman home atau jhdata. Menggunakan token lama."
        NEW_XSRF_TOKEN=$(cat "$XSRF_TOKEN_FILE") # Fallback ke token sebelumnya
    else
        echo "   XSRF Token baru dari jhdata: $NEW_XSRF_TOKEN"
    fi
else
    echo "   XSRF Token baru dari form: $NEW_XSRF_TOKEN"
fi
echo "$NEW_XSRF_TOKEN" > "$XSRF_TOKEN_FILE" # Simpan token baru

# 4. Meminta JupyterHub untuk Spawn Server (Ini adalah langkah baru!)
echo "4. Meminta JupyterHub untuk me-spawn server untuk $USERNAME..."
# Data form ini harus sesuai dengan apa yang diharapkan JupyterHub kamu
# Cek /hub/spawn HTML form untuk detailnya
SPAWN_FORM_DATA="profile_id=$PROFILE_ID&profile_name=$PROFILE_NAME&image=$IMAGE_NAME&node_count_final=1&primary_node=$PRIMARY_NODE&selected_nodes=%5B%7B%22hostname%22%3A%22$PRIMARY_NODE%22%2C%22ip_address%22%3A%2210.33.17.30%22%7D%5D&_xsrf=$(cat "$XSRF_TOKEN_FILE")"

# Note: selected_nodes perlu di-URL encode jika itu adalah JSON string
# Contoh: [{"hostname":"rpl-02","ip_address":"10.33.17.30"}]
# URL-encoded: %5B%7B%22hostname%22%3A%22rpl-02%22%2C%22ip_address%22%3A%2210.33.17.30%22%7D%5D
# Saya mengasumsikan struktur selected_nodes ini dari mass.py. Sesuaikan jika berbeda.

SPAWN_RESPONSE=$(curl -s -L -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "$SPAWN_FORM_DATA" \
    "$JUPYTERHUB_URL/hub/spawn" \
    -D "$TEMP_DIR/spawn_header.txt")

SPAWN_STATUS_CODE=$(grep HTTP/1.1 "$TEMP_DIR/spawn_header.txt" | awk '{print $2}' | tail -n 1)

if [[ "$SPAWN_STATUS_CODE" == "302" || "$SPAWN_STATUS_CODE" == "303" ]]; then
    echo "   Permintaan spawn server berhasil dikirim (status $SPAWN_STATUS_CODE)."
else
    echo "ERROR: Gagal mengirim permintaan spawn server (status $SPAWN_STATUS_CODE)."
    echo "Respons penuh:"
    echo "$SPAWN_RESPONSE"
    rm -f "$COOKIE_FILE" "$XSRF_TOKEN_FILE"
    exit 1
fi

# 5. Polling status server hingga siap
echo "5. Polling status server hingga siap (maks 120 detik)..."
SERVER_READY=false
START_TIME=$(date +%s)
TIMEOUT=120
while [ "$(($(date +%s) - START_TIME))" -lt "$TIMEOUT" ]; do
    SERVER_PROGRESS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -H "X-XSRFToken: $(cat "$XSRF_TOKEN_FILE")" "$JUPYTERHUB_URL/hub/api/users/$USERNAME/server/progress")
    
    # Periksa status code dari respons progress.
    # Jika 200 OK dan ready: true, maka berhasil.
    # Jika 404, mungkin masih di tahap awal atau URL salah.
    # Jika 400 atau error lain, mungkin ada masalah serius.
    PROGRESS_STATUS_CODE=$(echo "$SERVER_PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")

    if [ "$PROGRESS_STATUS_CODE" == "200" ] && echo "$SERVER_PROGRESS_RESPONSE" | grep -q '"ready": true'; then
        echo "   Server JupyterLab berhasil di-spawn dan siap."
        SERVER_READY=true
        break
    elif [ "$PROGRESS_STATUS_CODE" == "404" ]; then
        echo "   Server progress API 404, server mungkin masih booting atau belum terdaftar. Mencoba lagi..."
    elif [ "$PROGRESS_STATUS_CODE" == "400" ]; then
         echo "   Server progress API 400, pesan: $(echo "$SERVER_PROGRESS_RESPONSE" | grep -oP '"message": "\K[^"]+') Mencoba lagi..."
    else
        echo "   Menunggu server siap... Status: $(echo "$SERVER_PROGRESS_RESPONSE" | grep -oP '"message": "\K[^"]+' || echo "Status tak dikenal: $SERVER_PROGRESS_RESPONSE")"
    fi
    sleep 5
done

if [ "$SERVER_READY" = false ]; then
    echo "ERROR: Timeout menunggu server JupyterLab siap setelah $TIMEOUT detik. Server mungkin gagal spawn."
    rm -f "$COOKIE_FILE" "$XSRF_TOKEN_FILE"
    exit 1
fi

# 6. Membuat Kernel JEG
echo "6. Membuat kernel JEG dengan spesifikasi '$KERNEL_SPEC_NAME'..."
KERNEL_CREATE_PAYLOAD="{\"name\": \"$KERNEL_SPEC_NAME\"}"
KERNEL_CREATE_RESPONSE=$(curl -s -b "$COOKIE_FILE" \
    -H "X-XSRFToken: $(cat "$XSRF_TOKEN_FILE")" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "$KERNEL_CREATE_PAYLOAD" \
    "$JUPYTERHUB_URL/user/$USERNAME/api/kernels")

KERNEL_ID=$(echo "$KERNEL_CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

if [ -z "$KERNEL_ID" ]; then
    echo "ERROR: Gagal membuat kernel. Respons: $KERNEL_CREATE_RESPONSE"
    rm -f "$COOKIE_FILE" "$XSRF_TOKEN_FILE"
    exit 1
fi
echo "$KERNEL_ID" > "$KERNEL_ID_FILE"
echo "   Kernel JEG berhasil dibuat dengan ID: $KERNEL_ID"

echo "=== Proses Selesai ==="
echo "Kamu sekarang memiliki ID kernel di $KERNEL_ID_FILE dan cookie di $COOKIE_FILE."
echo "Untuk menghapus kernel nanti, kamu bisa gunakan:"
echo "curl -X DELETE -b \"$COOKIE_FILE\" -H \"X-XSRFToken: $(cat "$XSRF_TOKEN_FILE")\" \"$JUPYTERHUB_URL/user/$USERNAME/api/kernels/$KERNEL_ID\""

rm -rf "$TEMP_DIR" # Hapus komentar jika ingin membersihkan otomatis