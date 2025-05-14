variable "alpine_320_img_url" {
  description = "alpine 3.20 image"
  default     = "https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/cloud/generic_alpine-3.20.5-x86_64-bios-cloudinit-r0.qcow2"
}

variable "img_path" {
  description = "alpine 3.20 image local path"
  default     = "default"
}

variable "interface" {
  type    = string
  default = "eth0"
}

variable "master_ips" {
  type    = list(any)
  default = ["192.168.122.20"]
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
  default = ["alpine-master"]
}

#application server
variable "app_ips" {
  type    = list(any)
  default = ["192.168.122.21", "192.168.122.22"]
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
  default = ["alpine-worker1","alpine-worker2"]
}
