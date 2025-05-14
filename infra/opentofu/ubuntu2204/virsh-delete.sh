for vm in k3s-master k3s-worker1 k3s-worker2; do
    virsh shutdown $vm
    virsh undefine --remove-all-storage $vm
done

virsh list --all
