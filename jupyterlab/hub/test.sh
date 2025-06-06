#!/bin/bash

echo "🔍 Testing Hub <-> Container Connectivity"
echo "========================================"

# Get current container info
CONTAINER_ID=$(docker ps --filter "name=jupyterlab-admin" --format "{{.ID}}")
REMOTE_IP="10.21.73.122"

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ No running JupyterLab container found"
    exit 1
fi

echo "📦 Found container: $CONTAINER_ID"
echo "🌐 Remote IP: $REMOTE_IP"

echo ""
echo "1. 🏓 Test hub can reach remote IP:"
ping -c 2 $REMOTE_IP

echo ""
echo "2. 🔍 Check hub listening ports:"
netstat -tlnp | grep :8081

echo ""
echo "3. 🎯 Test hub API from local:"
curl -f http://localhost:8081/hub/api 2>/dev/null && echo "✅ Hub API accessible locally" || echo "❌ Hub API not accessible"

echo ""
echo "4. 📡 Get VPN/accessible IP:"
VPN_IP=$(ip route get $REMOTE_IP 2>/dev/null | grep src | awk '{print $7}')
if [ ! -z "$VPN_IP" ]; then
    echo "VPN/Route IP: $VPN_IP"
    echo "Testing hub API via VPN IP:"
    curl -f http://$VPN_IP:8081/hub/api 2>/dev/null && echo "✅ Hub API accessible via $VPN_IP" || echo "❌ Hub API not accessible via $VPN_IP"
else
    echo "❌ Could not determine VPN IP"
fi

echo ""
echo "5. 🐳 Test from inside container (if reachable):"
if docker exec -it $CONTAINER_ID curl --connect-timeout 5 -f http://localhost:8081/hub/api 2>/dev/null; then
    echo "✅ Container can reach hub via localhost"
elif [ ! -z "$VPN_IP" ] && docker exec -it $CONTAINER_ID curl --connect-timeout 5 -f http://$VPN_IP:8081/hub/api 2>/dev/null; then
    echo "✅ Container can reach hub via $VPN_IP"
else
    echo "❌ Container cannot reach hub"
    echo "Container logs (last 10 lines):"
    docker logs $CONTAINER_ID --tail 10
fi

echo ""
echo "6. 💡 Recommendations:"
echo "   - Ensure hub binds to 0.0.0.0:8081 (not localhost)"
echo "   - Container env should use accessible IP: JUPYTERHUB_API_URL=http://$VPN_IP:8081/hub/api"
echo "   - Check firewall allows $REMOTE_IP -> hub_ip:8081"