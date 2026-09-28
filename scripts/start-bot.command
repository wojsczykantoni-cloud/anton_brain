#!/bin/bash
cd ~/anton_brain || exit 1

export NVM_DIR="$HOME/.nvm"
export PATH="$NVM_DIR/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

node bot.js
