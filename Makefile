build:
	docker build -t fastapi-app:latest .

up: build
	minikube start
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml

down:
	kubectl delete -f k8s/deployment.yaml
	kubectl delete -f k8s/service.yaml
	minikube stop

logs:
	kubectl logs -l app=fastapi-app -f

service:
	minikube service fastapi-service
