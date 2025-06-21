#!/bin/bash
ray start --head --num-gpus=0 --dashboard-host 0.0.0.0 --block --resources="{\"$1\":$2}"