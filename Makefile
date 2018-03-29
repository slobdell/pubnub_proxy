TARGET_PORT="3001"
IMAGE_NAME="pubnub-proxy-image"
TAG_NAME="latest"
TARGET_MACHINE_NAME="da-fino-2"

CANONICAL_ID="$(IMAGE_NAME):$(TAG_NAME)"

serve:
	FLASK_APP=proxy_server.py env/bin/flask run -h 0.0.0.0 -p 3001


create_machine:
	docker-machine create --driver digitalocean  --digitalocean-size s-1vcpu-1gb --digitalocean-image "ubuntu-16-04-x64" --digitalocean-region "sfo2" --digitalocean-access-token $(DIGITAL_OCEAN_TOKEN) $(TARGET_MACHINE_NAME)

get_ip_address:
	docker-machine ls


build_docker_image:
	docker build -t slobdell/$(CANONICAL_ID) .

upload_container_image:
	docker push slobdell/$(IMAGE_NAME)

remote:
	echo "Run this command locally..."
	eval $(docker-machine env da-fino-2)
	# docker login

run_docker:
	docker run -d -p 80:$(TARGET_PORT) --name pubnub-proxy slobdell/$(CANONICAL_ID)

stop:
	docker rm -f pubnub-proxy

destroy_machine:
	docker-machine rm $(TARGET_MACHINE_NAME)
