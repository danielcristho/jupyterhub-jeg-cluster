variable "debian12_img_url" {
  description = "debian 12 image"
  default     = "https://cdimage.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
}

variable "img_path" {
  description = "debian 12 image local path"
  default     = "default"
}

variable "interface" {
  type    = string
  default = "ens3"
}

#load balancer
variable "master_ips" {
  type    = list(any)
  default = ["192.168.122.30"]
}

variable "master_memory" {
  type    = string
  default = "4096"
}

variable "master_vcpu" {
  type    = number
  default = 4
}

variable "master_disk" {
  type    = number
  default = "21474836480"
}

variable "master_hostname" {
  type    = list(string)
  default = ["k3s_master"]
}

#application server
variable "app_ips" {
  type    = list(any)
  default = ["192.168.122.31", "192.168.122.32"]
}

variable "app_memory" {
  type    = string
  default = "2048"
}

variable "app_vcpu" {
  type    = number
  default = 2
}

variable "app_disk" {
  type    = number
  default = "21474836480"
}

variable "app_hostname" {
  type    = list(string)
  default = ["k3s_worker_1","k3s_worker_2"]
}
