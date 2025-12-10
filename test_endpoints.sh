export APP_URL='https:/YOUR-APP-NAME.up.railway.app/'

echo "🔍 Quick Endpoint Test"
echo "Testing: $APP_URL"
echo ""

# Health
echo "1️⃣  Health:"
curl -s "$APP_URL/health" | head -1

# Docs
echo "2️⃣  Docs:"
curl -I -s "$APP_URL/docs" | grep "HTTP"

# Google OAuth
echo "3️⃣  Google OAuth:"
curl -I -s "$APP_URL/auth/google" | grep "HTTP"

echo ""
echo "✅ Replace YOUR-APP-NAME in the script and run: bash test_endpoints.sh"
