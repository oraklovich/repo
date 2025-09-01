#!/bin/bash

echo "🚀 Запуск футбольного бота в Minikube..."

# Запускаем Minikube
echo "1. Запускаем Minikube..."
minikube start --driver=docker

# Настраиваем окружение Docker
echo "2. Настраиваем окружение Docker..."
eval $(minikube docker-env)

# Проверяем образы
echo "3. Проверяем Docker образы..."
docker images | grep -E '(scores-parser|football-bot)'

# Если образов нет - собираем
if ! docker images | grep -q "scores-parser"; then
    echo "Собираем образ scores-parser..."
    docker build -f Dockerfile.parser -t scores-parser .
fi

if ! docker images | grep -q "football-bot"; then
    echo "Собираем образ football-bot..."
    docker build -f Dockerfile.bot -t football-bot .
fi

# Запускаем приложения
echo "4. Запускаем приложения в Kubernetes..."
kubectl apply -f scores-deployment.yaml
kubectl apply -f football-bot-deployment.yaml

# Ждем запуска
echo "5. Ждем запуска подов..."
sleep 15

# Показываем статус
echo "6. Статус системы:"
kubectl get pods
kubectl get services

echo "✅ Система запущена!"
echo "📋 Команды для управления:"
echo "   Просмотр логов бота:    kubectl logs -l app=football-bot -f"
echo "   Просмотр логов парсера: kubectl logs -l app=scores-parser -f"
echo "   Остановить Minikube:    minikube stop"
echo "   Удалить все:            kubectl delete -f scores-deployment.yaml -f football-bot-deployment.yaml"
