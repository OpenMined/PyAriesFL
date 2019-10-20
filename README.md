# Team-43
Distributed Deep-learning DID-acts


# Inspiration

We are PhD students focused on privacy-preserving methods and techniques. Diffusion allows us to experiment, build, learn and test technologies that are too new for academia, in a short amount of time. We have experience in our team of both Identity technologies and decentralised machine learning and wanted to see how we could combine these two disciplines. The hyperledger aries secure messaging capability recently demonstrated by BC Gov at a conference seemed an interesting place to start.
What it does

Our project allows the participants to create a secure channel using DID communication. This channel can then be authenticated with relevant participants requesting credentials to ensure that the correct people are able to contribute to the learning, and reviece the trained model. Ie reduces the likelihood of a malicious learning or malicious researcher.

A trusted source as the NHS Head Office issued the credentials to the participants, and a regulatory authority granted the researcher's credentials. After the credentials validation from each side using the public DIDs, the researcher sends his model to each participant with confidence that they are legitimate. The participants train their raw data, and a secure aggregator summarizes their outputs before sent back to the researcher.

The final federated trained model defends the researcher from malicious misuses such as model poisoning attacks, and in the same time, it is protecting the privacy of the participants since their raw data never left their premises.
How we built it

We created the secured communication channel using Hyperledger Aries. The DID of each entity is stored in a blockchain. The infrastructure is blockchain-agnostic.

We gathered mental health data relating to a survey taken by developers in 2014 [link](https://www.kaggle.com/osmi/mental-health-in-tech-survey). The dataset was federated into three batches; these three batches included in our three hospital containers, respectively. Our learning coordinator begins with an untrained model. When our learning protocol begins, the coordinator sends the untrained deep neural-network (DNN) to the first hospital, this hospital cleans its dataset, trains the DNN and sends it back to the coordinator once completed.

The coordinator then sends the updated model to the next hospital and waits for this hospital to perform the cleaning and training tasks. This process continues until each hospital has trained the model with its data. At the end of the training process, the researcher concludes with a model which trained over n batches, where n is the number of hospitals.
Challenges we ran into

We struggled with docker at times. We also planned to add a UI for visual explanation, but struggled with adapting the aries agents to a web server - this was completed. We then had issues with CORS, which we were unable to resolve in time.

# Accomplishments that we're proud of

We got to grips with the new hyperledger aries code base and cloud agent provided by the government of British Columbia. Building a complex ecosystem of issuers, verifiers and holders. We also built a federated machine learning model enabling learning to take place without data needing to leave it's original silo. We believe Hyperledger Aries can help solve the problem of secure communication between the coordinator and learners as well as enabling trust within decentralised machine learning systems.
What we learned

We explored the identity-credentials system in a complex real-world scenario, where researchers need to send their model to the participants to protect their privacy, but in the same time, they have to be protected against malicious unauthorized training.
What's next for Distributed Deep-learning DID-acts

One of the biggest unknows for us was whether the DIDComm protocol in aries could support the type of messages required to be passed between partipants in federated machine learning. The next step for this project would be to work with the Hyperledger Aries Working group to define a aries rfc for a protocol specifically designed for this use case.

# Built With

    deep-learning
    did
    docker
    federated-learning
    flask
    hyperledger-aries
    hyperledger-indy
    containerisation
    python

# Submitted to

    Diffusion 2019

# Created by

    **Will Abramson** 
    **Adam James Hall**
    **Pavlos Papadopoulos**