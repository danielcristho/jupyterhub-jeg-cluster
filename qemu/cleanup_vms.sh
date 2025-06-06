#!/bin/bash

for vm in $(virsh list --name); do
  echo "Shutting down $vm..."
  virsh destroy "$vm"
done

for vm in $(virsh list --all --name); do
  echo "Undefining $vm..."
  virsh undefine "$vm" --remove-all-storage --nvram
done

echo "Cleaning up disk images..."
rm -v /var/tmp/images/*.qcow2
rm -v /var/tmp/images/seed-*.iso

echo "✅ All VMs are deleted"