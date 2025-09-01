#!/bin/bash

echo "🛑 Останавливаем систему..."

# Останавливаем приложения
kubectl delete -f scores-deployment.yaml -f football-bot-deployment.yaml

# Останавливаем Minikube
minikube stop

echo "✅ Система остановлена!"
