FROM maven:3.6.1-jdk-8

ENV PYTHONUNBUFFERED 1
ENV HUNOR_MAVEN_PLUGIN_VERSION 0.3.0

RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y python3 python3-pip graphviz
RUN mvn org.apache.maven.plugins:maven-dependency-plugin:get \
    -Dartifact=br.ufal.ic.easy.hunor.plugin:hunor-maven-plugin:$HUNOR_MAVEN_PLUGIN_VERSION \
    -DremoteRepositories=marcioaug::::https://raw.githubusercontent.com/marcioaug/mvn/repo
RUN rm /root/.m2/repository/br/ufal/ic/easy/hunor/plugin/hunor-maven-plugin/$HUNOR_MAVEN_PLUGIN_VERSION/_remote.repositories

ADD . /opt/hunor

RUN pip3 install -U /opt/hunor
