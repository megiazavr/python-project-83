#!/usr/bin/env bash
# Скачиваем uv и устанавливаем зависимости
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
make install

chmod +x build.sh
