#!/bin/bash

# Base paths
BASE_IMAGE="/var/tmp/images/base.qcow2"
IMAGES_DIR="/var/tmp/images"
CLOUDINIT_DIR="/var/tmp/cloudinit"

mkdir -p "$CLOUDINIT_DIR"

# Define VM configurations
VM_NAMES=("rpl-worker-0" "rpl-worker-1" "rpl-worker-2")
STATIC_IPS=("10.21.73.201" "10.21.73.202" "10.21.73.203")

# VM resources
RAM_MB=8192
VCPUS=4

# SSH public key
SSH_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILnbiFnwahDaIl3UpgIviSSa319z4RnNcwbRPk7fPUQZ daniel@rpl"

# Loop over VMs
for i in "${!VM_NAMES[@]}"; do
  VM_NAME="${VM_NAMES[$i]}"
  STATIC_IP="${STATIC_IPS[$i]}"

  echo "Creating VM: $VM_NAME with IP: $STATIC_IP"

  # Clone base image
  qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMAGE" "$IMAGES_DIR/${VM_NAME}.qcow2" 25G

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
    gateway4: 10.21.73.1
    nameservers:
      addresses: [8.8.8.8, 202.46.129.2, 202.46.129.3]
EOF

  # Generate seed.iso
  cloud-localds --network-config "$NETWORK_CONFIG_FILE" "$IMAGES_DIR/seed-${VM_NAME}.iso" "$USER_DATA_FILE"

  # Create VM with virt-install using bridged network
  virt-install \
    --name "$VM_NAME" \
    --memory "$RAM_MB" \
    --vcpus "$VCPUS" \
    --disk path="$IMAGES_DIR/${VM_NAME}.qcow2",format=qcow2 \
    --disk path="$IMAGES_DIR/seed-${VM_NAME}.iso",device=cdrom \
    --import \
    --os-variant ubuntu22.04 \
    --network bridge=br0,model=virtio \
    --graphics vnc,listen=0.0.0.0 \
    --noautoconsole \
    --noreboot

done

echo "All VMs created successfully!"
