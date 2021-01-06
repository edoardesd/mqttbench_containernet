docker exec -it mn.rabbitmq1 rabbitmqctl cluster_status
docker exec -it mn.rabbitmq1 rabbitmqctl stop_app
docker exec -it mn.rabbitmq1 rabbitmqctl join_cluster rabbit@rabbitmq0
docker exec -it mn.rabbitmq1 rabbitmqctl start_app
docker exec -it mn.rabbitmq2 rabbitmqctl stop_app
docker exec -it mn.rabbitmq2 rabbitmqctl join_cluster rabbit@rabbitmq0
docker exec -it mn.rabbitmq2 rabbitmqctl start_app
docker exec -it mn.rabbitmq3 rabbitmqctl stop_app
docker exec -it mn.rabbitmq3 rabbitmqctl join_cluster rabbit@rabbitmq0
docker exec -it mn.rabbitmq3 rabbitmqctl start_app
docker exec -it mn.rabbitmq3 rabbitmqctl cluster_status
docker exec -it mn.rabbitmq4 rabbitmqctl stop_app
docker exec -it mn.rabbitmq4 rabbitmqctl join_cluster rabbit@rabbitmq0
docker exec -it mn.rabbitmq4 rabbitmqctl start_app
docker exec -it mn.rabbitmq2 rabbitmqctl cluster_status
