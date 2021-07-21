import os
import docker
import random
import time

# Seconds between each attack occasion.
attack_interval = 5

# Containers that the antagonist must avoid when randomly selecting a container to stop.
safe_containers = ["/agent"]

client = docker.from_env()


def stop_random_container() -> None:
    """
    Picks a random container running on the host and stops it.
    """
    # We retrieve the active containers running on the host and we filter them using an boolean function
    # defined below to exclude the containers listed in safe_containers.
    containers = client.containers.list()
    filtered_containers = list(filter(filter_containers, containers))

    # If at least one container remains, we generate a random number to
    # select the target of the attack
    if len(filtered_containers) > 0:
        num = random.randint(0, len(filtered_containers) - 1)

        # We stop the selected container
        filtered_containers[num].stop()
        print(filtered_containers[num].attrs.get("Name") + " has been stopped.")


def change_loss() -> None:
    """
    Changes the percentage of packet loss that is simulated on the network to a random number.
    """

    # We generate a random number between 10 and 80 that will be the next
    # value for the simulated packet loss
    num = random.randint(10, 40)
    loss = str(num) + "%"
    print("Packet loss changed to " + loss)

    # We remove eventual existing rules and we add a new rule, setting the packet loss
    # percentage to simulate
    os.system("tc qdisc del dev eth0 root")
    os.system("tc qdisc add dev eth0 root netem loss " + loss)


# Utility function used to filter the containers depending on their name.
# Returns True when the container name is not part of the safe_containers list, false otherwise.
def filter_containers(container):
    if container.attrs.get("Name") in safe_containers:
        return False
    return True


# The antagonist repeats the following actions as long as it is executing.
while True:
    try:
        # We generate a random number between 1 and 5, then we check if the resulting number is higher than 4.
        # This will be true in approximately 20% of the iterations.
        if random.randint(1, 5) > 4:
            # If the condition is verified, the antagonist proceeds with an attack to a random container.
            stop_random_container()

        # We generate a random number between 1 and 10, then we check if the resulting number is higher than 7.
        # This will be true in approximately 30% of the iterations.
        if random.randint(1, 10) > 7:
            # If the condition is verified, the antagonist changes the current packet loss simulated on the network.
            change_loss()

        # The antagonist will sleep for some time and be ready for the next iteration
        # in attack_interval seconds
        time.sleep(attack_interval)

    except Exception:
        # In case of exceptions, the antagonist will just sleep until its time for the next iteration
        time.sleep(attack_interval)
        continue
