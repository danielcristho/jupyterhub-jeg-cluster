#!/bin/bash

# Base paths
BASE_IMAGE="/var/tmp/images/base.qcow2"
IMAGES_DIR="/var/tmp/images"
CLOUDINIT_DIR="/var/tmp/cloudinit"

mkdir -p "$CLOUDINIT_DIR"

# Define VM configurations
# VM_NAMES=("rpl-worker-0" "rpl-worker-1" "rpl-worker-2")
# STATIC_IPS=("192.168.122.50" "192.168.122.51" "192.168.122.52")

VM_NAMES=("worker1" "worker2")
STATIC_IPS=("192.168.122.98" "192.168.122.99")

# VM resources
RAM_MB=4096
VCPUS=2

# SSH public key
SSH_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDCHbYYh5tqg9exO3nqzWzCA4sawLlh7hRMdmFccxkhcRtQxi75tNGv92trAdWW1nbXLz9ZIybGg2uQPr0hgVJrnkgcNM3zEN0a83RcfAw0klci31OEU/gRpqqRmZMyRRtPrhavk78FHMwxpHBGpyxrVCSeXwKln+EtcLtjrWBQUatFR7+c19OXffmizjoI1Qyw8FOZETy8Hwu+K6EH3hQ3kPcA+AFHA3lxd9BRw/XuNG9MHXWL+0cmqeddGKG0OWdTvcU0/ZSoIR9FO3yei+Rbtyos5QkOmiSVv6hwipIkx0ji4CeUJ9XRjkNsIP9FHpwuqkLUMqg4K4TjG4X4FxT3xh/jRQsc3BYPCVhzbfws+C7iAYxOvlQm1ikZBsvRQkwbc4aS+NayxfKqn7c8HV6zFc8FRJf8c6h/odCEYs2J7OdZKdOuDVwZUqvqBvDnxPAe8YMVt8iG5jwqa2XFz+GNkJLdyvGIk8IOq7hRrhBu6rtDkV7SHOoKfXeD5g1im91LwZzRQfqfmD2swF8MoLVOI3YRPAYYqB3MqeMpdwTzW1yOLLMkfyJOA8iw5vhXXQt1Ed6in3Dtvc4p8rfRiUASZD/PWHFdlqS/ybGSlh+1C5BjJb601sKozZmAR5f8KS6y34NoYoMjg5Ug0LHGX3cetN4QeetHLvvrWcV8ZpmQWw== pepuhodaniel93@gmail.com"

# Loop over VMs
for i in "${!VM_NAMES[@]}"; do
  VM_NAME="${VM_NAMES[$i]}"
  STATIC_IP="${STATIC_IPS[$i]}"

  echo "Creating VM: $VM_NAME with IP: $STATIC_IP"

  # Clone base image
  qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMAGE" "$IMAGES_DIR/${VM_NAME}.qcow2" 10G

  # Create per-VM user-data
  USER_DATA_FILE="$CLOUDINIT_DIR/user-data-$VM_NAME"
  NETWORK_CONFIG_FILE="$CLOUDINIT_DIR/network-config-$VM_NAME"

  cat > "$USER_DATA_FILE" <<EOF
#cloud-config
hostname: $VM_NAME
users:
  - name: ray
    gecos: ray
    groups: [sudo]
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    home: /home/ray
    shell: /bin/bash
    lock_passwd: false
    ssh_authorized_keys:
      - $SSH_KEY
chpasswd:
  list: |
    root:whoami
  expire: false
ssh_pwauth: true
disable_root: false
runcmd:
  - sed -i '/PermitRootLogin/d' /etc/ssh/sshd_config
  - echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
  - systemctl restart sshd
  - apt-get update
  - apt-get install -y qemu-guest-agent
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
EOF

  # Create per-VM network-config
  cat > "$NETWORK_CONFIG_FILE" <<EOF
version: 2
ethernets:
  enp1s0:
    dhcp4: false
    addresses: [$STATIC_IP/24]
    gateway4: 192.168.122.1
    nameservers:
      addresses: [8.8.8.8]
EOF

  # Generate seed.iso
  cloud-localds --network-config "$NETWORK_CONFIG_FILE" "$IMAGES_DIR/seed-${VM_NAME}.iso" "$USER_DATA_FILE"

  # Create VM with virt-install
  virt-install \
    --name "$VM_NAME" \
    --memory "$RAM_MB" \
    --vcpus "$VCPUS" \
    --disk path="$IMAGES_DIR/${VM_NAME}.qcow2",format=qcow2 \
    --disk path="$IMAGES_DIR/seed-${VM_NAME}.iso",device=cdrom \
    --import \
    --os-variant ubuntu22.04 \
    --network network=default \
    --graphics vnc,listen=0.0.0.0 \
    --noautoconsole

done

echo "All VMs created successfully!"