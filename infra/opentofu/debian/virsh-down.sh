for vm in k3s_master k3s_worker_1 k3s_worker_2; do
    virsh shutdown $vm
done

virsh list --all

