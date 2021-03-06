import pandas as pd
import numpy as np
import logs
from annotate import getManualAnnotation
from sklearn.feature_extraction.text import CountVectorizer,TfidfTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import cross_val_score,train_test_split
from sklearn.metrics import f1_score,precision_score,recall_score,confusion_matrix,classification_report
from textblob import TextBlob
from sklearn.utils import shuffle
from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import StratifiedKFold
#from nltk.classify.scikitlearn import SklearnClassifier

def createInitialTrainingSet(df_data,count,label):
    
    '''
    Randomly selects the requirement combinations and get's them annotated by the user and marks them Labelled - 'M'. 
    Returns the updated dataset.
    '''
    i=0  #Counter Variable
    logs.writeLog("\nPlease annotate the following requirement combinations...(For Training Set)")
    
    while i<count:
        logs.writeLog("\nCombination "+str(i+1)+" .....")
        
        #The requirement combination is updated and added to the dataFrame
        if label == 'BinaryClass':
            selection = df_data[df_data['BLabelled']=='A'].sample(1)  #Samples one requirement combination which is To Be annotated ie. Marked as 'A'
            selectedIndex = selection.index.values[0]
            selection.reset_index(inplace=True)
            
            #Get the requirements
            req1_id = selection.loc[0,'req1_id']
            req2_id = selection.loc[0,'req2_id']
            req1 = selection.loc[0,'req1']   
            req2 = selection.loc[0,'req2']
            
            #logs.writeLog("Removed Index : "+str(selectedIndex))
            df_data.drop(index=selectedIndex,inplace=True)  #Drops the particular requirement combination from the original DataFrame
            
            df_userAnnot = pd.DataFrame(columns = df_data.columns)
            userAnnot = getManualAnnotation(req1_id,req2_id,req1,req2,label) #User provides the annotation for the requirement combination
            
            if userAnnot == "exit":
                raise Exception ('\nExited the Program successfully!')
            
            df_userAnnot = df_userAnnot.append({'req1_id':req1_id,'req1':req1,'req2_id':req2_id,'req2':req2,'BinaryClass':userAnnot,'MultiClass':0,'BLabelled':'M','MLabelled':'A'},ignore_index=True)  #Added MultiClass as 0 because when we are learning BinaryClass... MultiClass can contain a dummy value.
            logs.createAnnotationsFile(df_userAnnot)
            
            df_data = pd.concat([df_data,df_userAnnot],axis=0) #Manually Annotated Values are concatenated with the original dataset and the resultant is returned.
            
        else:
            print (df_data)
            selection = df_data[df_data['MLabelled']=='A'].sample(1)  #Samples one requirement combination which is To Be annotated ie. Marked as 'A'
            selectedIndex = selection.index.values[0]
            selection.reset_index(inplace=True)
            
            #Get the requirements
            req1_id = selection.loc[0,'req1_id']
            req2_id = selection.loc[0,'req2_id']
            req1 = selection.loc[0,'req1']   
            req2 = selection.loc[0,'req2']
        
            #logs.writeLog("Removed Index : "+str(selectedIndex))
            df_data.drop(index=selectedIndex,inplace=True)  #Drops the particular requirement combination from the original DataFrame
            
            df_userAnnot = pd.DataFrame(columns = df_data.columns)
            userAnnot = getManualAnnotation(req1_id,req2_id,req1,req2,label) #User provides the annotation for the requirement combination
            
            if userAnnot == "exit":
                raise Exception ('\nExited the Program successfully!')
            
            df_userAnnot = df_userAnnot.append({'req1_id':req1_id,'req1':req1,'req2_id':req2_id,'req2':req2,'BinaryClass':1,'MultiClass':userAnnot,'BLabelled':'M','MLabelled':'M'},ignore_index=True)   #Added BinaryClass as 1 because we are learning the MultiClass labels only for the dependent Combinations (for which BinaryClass is 1)
            logs.createAnnotationsFile(df_userAnnot)

            df_data = pd.concat([df_data,df_userAnnot],axis=0) #Manually Annotated Values are concatenated with the original dataset and the resultant is returned.
            
        i=i+1

    
    logs.writeLog("Initial Manual Annotations completed.")
    
    return df_data

def createClassifier(clf,splitratio,df_labelledData,targetLabel):
    '''
    Creates and returns Count Vectorizer , tfidf Transformer, Classifier, Classifier Test Score, Length of train and test sets.
    '''
    # NOTE: NOT DELETING THE COMMENTED CODE SNIPPET AS IT MIGHT BE NEEDED IN FUTURE...
    
    #Convert numpy array of the training dataset.
    #trainData = np.array(trainData)
    #X_train = trainData[:,:-2]  #Keep Features aka requirement details in X_train
    #logs.writeLog("X_train : "+str(X_train))
    #y_train = trainData[:,-2].astype('int') #Keep the labels aka BinaryClass in y_train; update the datatype as int.
    #logs.writeLog("y_train : "+str(y_train))
    #print ("Inside Create Classifier")
    #print ("df_labelledData length : ",str(len(df_labelledData)))
    logs.writeLog("\nPerforming Balancing of Data....\n")
    df_labelledData[targetLabel] = df_labelledData[targetLabel].astype('int')    #Making sure the values are integer only and not float... 
    #######################################DATA BALANCING########################################################
    #Create empty dataframes to store the Balanced Combinations .... Making sure equal number of combinations corresponding to all label are available in train and test sets.
    df_testSet = pd.DataFrame(columns=df_labelledData.columns)
    df_trainSet = pd.DataFrame(columns=df_labelledData.columns)
    
    stats = df_labelledData[targetLabel].value_counts()  #Returns a series of number of different types of TargetLabels (values) available with their count.
    #print("Stats : "+str(stats))
    min_value_count = stats.min()  #Calculate minimum value count out of all labels.... will extract this number of combinations of each label type.
    #Calcalate the Test Size and Train Size... number of combinations to be sampled for each LABEL type.
    test_size = int(min_value_count*splitratio) if (int(min_value_count*splitratio)>=1) else 1  #added if else condition in case test size is less than 1. then minimum size should be 1.
    train_size = min_value_count - test_size
    #For each type of lab
    for key in stats.keys():
        #Sample out some values for Test Set
        df_sampleTest = df_labelledData[df_labelledData[targetLabel]==key].sample(test_size)
        df_labelledData = df_labelledData[~df_labelledData.isin(df_sampleTest)].dropna()  #Remove Sampled Values from original data set.
        df_testSet = pd.concat([df_testSet,df_sampleTest],axis=0)   #Add sampled values into the Test Set
        
        #Sample out some values for Train Set
        df_sampleTrain = df_labelledData[df_labelledData[targetLabel]==key].sample(train_size)
        df_labelledData = df_labelledData[~df_labelledData.isin(df_sampleTrain)].dropna()  #Remove Sampled Values from original data set.
        df_trainSet = pd.concat([df_trainSet,df_sampleTrain],axis=0)  #Add sampled values into the Test Set

    #Shuffle both Train and Test Set....
    df_trainSet = shuffle(df_trainSet)
    df_testSet = shuffle(df_testSet)

    #Split Train Test Sets into X_train,y_train,X_test,y_test   (Similar to Train Test Split....)
    #X_train = df_trainSet.loc[:,['req1','req2']] #Special characters are included in this as input is a list. 
    #y_train = df_trainSet.loc[:,targetLabel]
    #X_test = df_testSet.loc[:,['req1','req2']]
    #y_test = df_testSet.loc[:,targetLabel]
    
    #Combining the requirement 1 and requirement 2 in a single column.
    df_trainSet['req'] = df_trainSet['req1']+" "+df_trainSet['req2']
    df_testSet['req'] = df_testSet['req1']+" "+df_testSet['req2']
    
    X_train = df_trainSet.loc[:,'req']
    y_train = df_trainSet.loc[:,targetLabel]
    X_test = df_testSet.loc[:,'req']
    y_test = df_testSet.loc[:,targetLabel]
    
    #############################################################################################################
    
    #Train / Test Split (80/20)
    #X_train,X_test,y_train,y_test = train_test_split(df_labelledData.loc[:,['req1','req2']],df_labelledData.loc[:,targetLabel],test_size=splitratio)    
    #labelledData.iloc[:,:-2]  --> ['req1','req2]   labelledData.iloc[:,-2]  -->  ['BinaryClass' / 'MuliClass']
    
    logs.writeLog("\nTraining Set Size : "+str(len(X_train)))
    logs.writeLog("\nTrain Set Value Count : \n"+str(df_trainSet[targetLabel].value_counts()))

    logs.writeLog("\nTest Set Size : "+str(len(X_test)))
    logs.writeLog("\nTest Set Value Count : \n"+str(df_testSet[targetLabel].value_counts()))
    
    logs.writeLog("\n\nTraining Model.....")
    #Initialize Count Vectorizer which in a way performs Bag of Words on X_train
    #count_vect = CountVectorizer(tokenizer=lambda doc: doc, analyzer=split_into_lemmas, lowercase=False, stop_words='english')
    count_vect = CountVectorizer(lowercase = False, stop_words='english')
    X_train_counts= count_vect.fit_transform(np.array(X_train))
    
    #feature_names = count_vect.get_feature_names()  #--- Can be used for analysis if needed.
    #print ("\nFeature names : ", feature_names)
    #print (len(feature_names))
    #print ("\nBag Of Words :\n" ,repr(X_train_counts))
    #print (X_train_counts.toarray())
    #print (X_train_counts.toarray().shape)
    #input ("...............")
    
    tfidf_transformer = TfidfTransformer()
    X_train_tfidf= tfidf_transformer.fit_transform(X_train_counts)
    #print ("\nAfter TFIDF Transformation: \n",repr(X_train_tfidf))
    
    X_test_counts = count_vect.transform(np.array(X_test))
    X_test_tfidf = tfidf_transformer.transform(X_test_counts)
    
    #Random Forest Classifier Creation
    if clf == "RF" :
        clf_model = RandomForestClassifier().fit(X_train_tfidf, np.array(y_train).astype('int'))
        
        #Cross Validation Code Snippet...
        #clf_rdf = RandomForestClassifier()
        #scores = cross_val_score(clf_rdf,X_train_tfidf,y_train,cv=5)
        #logs.writeLog ("\nRandom Forest Classifier Cross Validation Score : "+str(scores.mean()))
    
        #predicted = clf_rdf.predict(X_test_tfidf)
        #print ("Prediction quality:" + str(np.mean(predicted == y_test)))

    #Naive Bayes Classifier Creation
    elif clf == "NB":
        clf_model = MultinomialNB().fit(X_train_tfidf,np.array(y_train).astype('int'))

    #Support Vector Machine Classifier Creation.
    elif clf == "SVM":
        clf_model = SVC(C=1.0, cache_size=200, class_weight=None, coef0=0.0, decision_function_shape='ovr', degree=3, gamma=1.0, kernel='rbf', max_iter=-1, probability=True, random_state=None, shrinking=True, tol=0.001, verbose=False).fit(X_train_tfidf,np.array(y_train).astype('int'))
    
    '''
    #Ensemble Creation
    elif clf == "ensemble":
        training = zip(X_train_tfidf,np.array(y_train).astype('int'))
        names = ['Random Forest','Naive Bayes','Support Vector Classifier']
        classifiers = [RandomForestClassifier(),MultinomialNB(),SVC(C=1.0, cache_size=200, class_weight=None, coef0=0.0, decision_function_shape='ovr', degree=3, gamma=1.0, kernel='rbf', max_iter=-1, probability=True, random_state=None, shrinking=True, tol=0.001, verbose=False)]
        models = zip(names,classifiers)
        print (type(models))
        clf_model = VotingClassifier(estimators=models,voting='hard',n_jobs=-1)
        clf_model = clf_model.fit(X_train_tfidf,np.array(y_train).astype('int')) #n_jobs = -1 makes allows models to be created in parallel (using all the cores, else we can mention 2 for using 2 cores)
    '''
    predict_labels = clf_model.predict(X_test_tfidf)
    actualLabels = np.array(y_test).astype('int')
    labelClasses = list(set(actualLabels))   #np.array(y_train).astype('int')
    #print ("labelClasses : ",labelClasses)
    clf_test_score = clf_model.score(X_test_tfidf,actualLabels)
    logs.writeLog ("\n"+clf+" Classifier Test Score : "+str(clf_test_score))
    
    #print (predict_labels)
    #print (actualLabels)
    
    f1 = round(f1_score(actualLabels, predict_labels,average='macro'),2)
    precision = round(precision_score(actualLabels, predict_labels,average='macro'),2)
    recall = round(recall_score(actualLabels, predict_labels,average='macro'),2)
    #logs.writeLog("\n\nF1 Score : "+str(f1))
    #logs.writeLog("\n\nPrecision Score : "+str(precision))                                                       
    #logs.writeLog("\n\nRecall Score : "+str(recall))
    logs.writeLog ("\n\nClassification Report : \n\n"+str(classification_report(actualLabels,predict_labels)))
    cm = confusion_matrix(actualLabels,predict_labels,labels=labelClasses)    
    logs.writeLog ("\n\nConfusion Matrix : \n"+str(cm)+"\n")
    #tn,fp,fn,tp = cm.ravel()
    #acc = round((tn+tp)/(tn+fp+fn+tp),2)
    #logs.writeLog ("\n\nAccuracy : "+str(acc))
    return count_vect, tfidf_transformer, clf_model,clf_test_score,len(X_train),len(X_test),f1,precision,recall  

def predictLabels(cv,tfidf,clf,df_toBePredictedData,targetLabel):
    '''
    Count Vectorizer (cv) applies Bag of Words on the Features 
    Next, tfidf Transformation is applied.
    predicts and returns the labels for the input data in a form of DataFrame.
    '''
    #predictData = np.array(df_toBePredictedData.loc[:,['req1','req2','BLabelled','MLabelled']])
    df_toBePredictedData['req']=df_toBePredictedData['req1']+" "+df_toBePredictedData['req2']
    predictData = np.array(df_toBePredictedData.loc[:,'req'])
    #logs.writeLog(str(df_toBePredictedData))
    
    predict_counts = cv.transform(predictData)
    predict_tfidf = tfidf.transform(predict_counts)
    predict_labels = clf.predict(predict_tfidf)
    predict_prob = clf.predict_proba(predict_tfidf)
    #predict_classes = clf.classes_
    #logs.writeLog(str(predict_classes))
    #logs.writeLog (str(type(predict_prob)))
    #logs.writeLog (str(predict_prob.shape))
    #clf_pred_score = round(np.mean(predict_labels == actualLabels),2)
    
    logs.writeLog ("\nTotal Labels Predicted : "+ str(len(predict_labels)))

    #f1 = round(f1_score(actualLabels, predict_labels,average='macro'),2)
    #precision = round(precision_score(actualLabels, predict_labels,average='macro'),2)
    #recall = round(recall_score(actualLabels, predict_labels,average='macro'),2)
    
    #print ("\nClassification Report : \n",classification_report(actualLabels,predict_labels))
    #cm = confusion_matrix(actualLabels,predict_labels,labels=[0,1])    
    #print ("\nConfusion Matrix : \n",cm)
    #tn,fp,fn,tp = cm.ravel()
    #acc = round((tn+tp)/(tn+fp+fn+tp),2)
    #print ("\nAccuracy : ",acc)
    
    if targetLabel =='BinaryClass':
        #Save the prediction results.... predictedProb saves the prediction probabilities in a list form for each prediction.
        #df_predictionResults = pd.DataFrame({'req1_id':df_toBePredictedData.loc[:,'req1_id'],'req1':df_toBePredictedData.loc[:],'req2':predictData[:,1],'BinaryClass':predict_labels[:],'MultiClass':0,'predictedProb':predict_prob.tolist(),'BLabelled':predictData[:,2],'MLabelled':predictData[:,3]})  #added 0 as dummy value to MultiClass because we are predicting BinaryClass
        df_toBePredictedData['BinaryClass']=predict_labels[:]
        df_toBePredictedData['MultiClass'] = 0
        df_toBePredictedData['predictedProb'] = predict_prob.tolist() 
        df_toBePredictedData['maxProb'] = np.amax(predict_prob,axis=1)
    else:
        #Save the prediction results.... predictedProb saves the prediction probabilities in a list form for each prediction.
        #df_predictionResults = pd.DataFrame({'req1':predictData[:,0],'req2':predictData[:,1],'BinaryClass':1,'MultiClass':predict_labels[:],'predictedProb':predict_prob.tolist(),'BLabelled':predictData[:,2],'MLabelled':predictData[:,3]})  #added 1 as Binary Class because we do MultiClass prediction only for dependent combinations.
        df_toBePredictedData['BinaryClass']= 1
        df_toBePredictedData['MultiClass'] = predict_labels[:]
        df_toBePredictedData['predictedProb'] = predict_prob.tolist() 
        df_toBePredictedData['maxProb'] = np.amax(predict_prob,axis=1)
    
    return df_toBePredictedData    #f1,precision,recall,clf_pred_score,acc
    
#ten fold cross validation for Blackline safety data set
def Tenfoldvalidation(cv,tfidf,clf_model,df_validationSet):
    
    df_validationSet['req'] = df_validationSet['req1']+" "+df_validationSet['req2']
    predictData = np.array(df_validationSet.loc[:,'req'])
    #logs.writeLog(str(predictData))
    actualLabels = np.array(df_validationSet.loc[:,'BinaryClass']).astype('int')
    predict_counts = cv.transform(predictData)
    predict_tfidf = tfidf.transform(predict_counts)
    print ("Inside Validate Classifier ")
    #print ("Predicted Labels : ",str(clf_model.predict(predict_tfidf)))
    #print ("Actual Labels : ",str(actualLabels))
    #clf_val_score = clf_model.score(predict_tfidf,actualLabels)
    crossv = StratifiedKFold(5)
    scores = cross_val_score(clf_model, predict_tfidf, actualLabels, cv=crossv) #https://scikit-learn.org/stable/modules/cross_validation.html
    print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

    return scores.mean()

def validateClassifier(cv,tfidf,clf_model,df_validationSet,targetLabel):
    print ("\nCalculating Validation Score.....\n")
    df_validationSet['req'] = df_validationSet['req1']+" "+df_validationSet['req2']
    predictData = np.array(df_validationSet.loc[:,'req'])
    #logs.writeLog(str(predictData))
    actualLabels = np.array(df_validationSet.loc[:,targetLabel]).astype('int')
    predict_counts = cv.transform(predictData)
    predict_tfidf = tfidf.transform(predict_counts)
    #print ("Inside Validate Classifier ")
    #print ("Predicted Labels : ",str(clf_model.predict(predict_tfidf)))
    #print ("Actual Labels : ",str(actualLabels))
    clf_val_score = clf_model.score(predict_tfidf,actualLabels)
    
    return clf_val_score
    
def split_into_lemmas(text):
    text = str(text)
    words = TextBlob(text).words
    return [word.lemmatize() for word in words]