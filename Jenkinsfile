pipeline {
    agent {
      node { 
        label 'py-uniformes'
      }
    }
    
    options {
      buildDiscarder(logRotator(numToKeepStr: '50', artifactNumToKeepStr: '50'))
      disableConcurrentBuilds()
      skipDefaultCheckout()  
    }
    
        
    stages {
      stage('CheckOut') {
        steps {
          checkout scm  
        }
       }
       
      stage('Docker build DEV') {
        when {
          branch 'development'
        }
          steps {
            sh 'echo Build Docker image'
                
        // Start JOB Rundeck para build das imagens Docker e push SME Registry
      
          script {
           step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
                               
              //JOB DE BUILD
              jobId: "8c184d21-ec1f-4a4d-9907-ff7c2973369a",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
           }
          }
      }

      stage('Deploy DEV') {
        when {
          branch 'development'
        }
          steps {
            sh 'echo Deploying desenvolvimento'            
       //Start JOB Rundeck para update de deploy Kubernetes DEV
         
         script {
            step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
              jobId: "69734996-1fcb-4cb1-9f16-643a38c7616c",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
           }
      
       
            }
        }
        
      stage('Docker build HOM') {
            when {
              branch 'homolog'
            }
            steps {
              sh 'echo build homologacao'
                
        // Start JOB Rundeck para build das imagens Docker e push registry SME
      
          script {
           step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
                
               
              //JOB DE BUILD
              jobId: "8bddeef2-0fd7-47fc-8775-dc7723f96ba6",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
           }
            } 
        }
      
      stage('Deploy HOM') {
            when {
                branch 'homolog'
            }
            steps {
                 timeout(time: 24, unit: "HOURS") {
               
                 telegramSend("${JOB_NAME}...O Build ${BUILD_DISPLAY_NAME} - Requer uma aprovação para deploy !!!\n Consulte o log para detalhes -> [Job logs](${env.BUILD_URL}console)\n")
                 input message: 'Deseja realizar o deploy?', ok: 'SIM', submitter: 'anderson_morais'
            }  


       //Start JOB Rundeck para update de imagens no host homologação 
         
         script {
            step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
              jobId: "a2cabd5f-c96d-4576-b385-c8a0543d6e92",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
           }
      
       
            }
        }

        stage('Docker Build PROD') {

            when {
              branch 'master'
            }
            steps {
                 timeout(time: 24, unit: "HOURS") {
               
                 telegramSend("${JOB_NAME}...O Build ${BUILD_DISPLAY_NAME} - Requer uma aprovação para deploy !!!\n Consulte o log para detalhes -> [Job logs](${env.BUILD_URL}console)\n")
                 input message: 'Deseja realizar o deploy?', ok: 'SIM', submitter: 'anderson_morais'
            }
                 sh 'echo Deploy produção'
                
        // Start JOB Rundeck para build das imagens Docker e push registry SME
      
          script {
           step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
            
               
              //JOB DE BUILD
              jobId: "c20d965c-7e50-4ada-b093-5c7856676430",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
           }
            }
        }

      stage('Deploy PROD') {
          when {
            branch 'master'
          }
          steps {
            timeout(time: 24, unit: "HOURS") {
              telegramSend("${JOB_NAME}...O Build ${BUILD_DISPLAY_NAME} - Requer uma aprovação para deploy !!!\n Consulte o log para detalhes -> [Job logs](${env.BUILD_URL}console)\n")
              input message: 'Deseja realizar o deploy?', ok: 'SIM', submitter: 'anderson_morais, bruno_alevato'
            }       
                
       //Start JOB Rundeck para deploy em produção 
         
         script {
            step([$class: "RundeckNotifier",
              includeRundeckLogs: true,
              jobId: "78bbdf0e-625e-42a6-8237-8a7d573a4f28",
              nodeFilters: "",
              //options: """
              //     PARAM_1=value1
               //    PARAM_2=value2
              //     PARAM_3=
              //     """,
              rundeckInstance: "Rundeck-SME",
              shouldFailTheBuild: true,
              shouldWaitForRundeckJob: true,
              tags: "",
              tailLog: true])
         }
        }
      }
     
}

}

