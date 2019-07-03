FROM maven:3.6.1-jdk-8

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y python3 python3-pip graphviz
RUN mvn org.apache.maven.plugins:maven-dependency-plugin:get \
    -Dartifact=br.ufal.ic.easy.hunor.plugin:hunor-maven-plugin:0.2.0 \
    -DremoteRepositories=marcioaug::::https://raw.githubusercontent.com/marcioaug/mvn/repo

ADD . /opt/hunor

RUN pip3 install -U /opt/hunor