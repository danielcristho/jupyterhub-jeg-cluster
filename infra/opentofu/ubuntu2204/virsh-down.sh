for vm in k3s-master k3s-worker1 k3s-worker2; do
    virsh shutdown $vm
done

virsh list --all

