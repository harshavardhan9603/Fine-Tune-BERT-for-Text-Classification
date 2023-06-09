# -*- coding: utf-8 -*-
"""Fine-Tune-BERT-for-Text-Classification-with-TensorFlow.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1OP4QDOnDc-0y701hMCjplfKTHTkTv3Iv

<h2 align=center> Fine-Tune BERT for Text Classification with TensorFlow</h2>

<div align="center">
    <img width="512px" src='https://drive.google.com/uc?id=1fnJTeJs5HUpz7nix-F9E6EZdgUflqyEu' />
    <p style="text-align: center;color:gray">Figure 1: BERT Classification Model</p>
</div>

In this project, you will learn how to fine-tune a BERT model for text classification using TensorFlow and TF-Hub.

The pretrained BERT model used in this project is available on [TensorFlow Hub](https://tfhub.dev/).

### Contents

This project/notebook consists of several Tasks.

- **Task 1**: Introduction to the Project.
- **Task 2**: Setup your TensorFlow and Colab Runtime
- **Task 3**: Download and Import the Quora Insincere Questions Dataset
- **Task 4**: Create tf.data.Datasets for Training and Evaluation
- **Task 5**: Download a Pre-trained BERT Model from TensorFlow Hub
- **Task 6**: Tokenize and Preprocess Text for BERT
- **Task 7**: Wrap a Python Function into a TensorFlow op for Eager Execution
- **Task 8**: Create a TensorFlow Input Pipeline with `tf.data`
- **Task 9**: Add a Classification Head to the BERT `hub.KerasLayer`
- **Task 10**: Fine-Tune BERT for Text Classification
- **Task 11**: Evaluate the BERT Text Classification Model

## Task 2: Setup your TensorFlow and Colab Runtime.

### Check GPU Availability

Check if your Colab notebook is configured to use Graphical Processing Units (GPUs). If zero GPUs are available, check if the Colab notebook is configured to use GPUs (Menu > Runtime > Change Runtime Type).

![Hardware Accelerator Settings](https://drive.google.com/uc?id=1qrihuuMtvzXJHiRV8M7RngbxFYipXKQx)
"""

!nvidia-smi

"""### Install TensorFlow and TensorFlow Model Garden"""

import tensorflow as tf
print(tf.version.VERSION)

!pip install -q tensorflow==2.12.0

!git clone --depth 1 -b v2.3.0 https://github.com/tensorflow/models.git

# install requirements to use tensorflow/models repository
!pip install -Uqr models/official/requirements.txt
# you may have to restart the runtime afterwards

"""## Task 3: Download and Import the Quora Insincere Questions Dataset"""

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import sys 
sys.path.append('models')
from official.nlp.data import classifier_data_lib
from official.nlp.bert import tokenization
from official.nlp import optimization

print("TF Version: ", tf.__version__)
print("Eager mode: ", tf.executing_eagerly())
print("Hub version: ", hub.__version__)
print("GPU is", "available" if tf.config.experimental.list_physical_devices("GPU") else "NOT AVAILABLE")

"""A downloadable copy of the [Quora Insincere Questions Classification data](https://www.kaggle.com/c/quora-insincere-questions-classification/data) can be found [https://archive.org/download/fine-tune-bert-tensorflow-train.csv/train.csv.zip](https://archive.org/download/fine-tune-bert-tensorflow-train.csv/train.csv.zip). Decompress and read the data into a pandas DataFrame."""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
df = pd.read_csv('https://archive.org/download/fine-tune-bert-tensorflow-train.csv/train.csv.zip',
                  compression = 'zip', low_memory ='False')
df.shape

df.tail(20)

df.target.plot(kind ='hist',title = 'targer distribution')

"""## Task 4: Create tf.data.Datasets for Training and Evaluation"""

train_df, remaining = train_test_split(df, random_state = 42, train_size=0.0075, stratify=df.target.values)
valid_df, _=train_test_split(remaining, random_state = 42, train_size=0.00075, stratify=remaining.target.values)
train_df.shape, valid_df.shape

with tf.device('/cpu:0'):
  train_data = tf.data.Dataset.from_tensor_slices((train_df['question_text'].values,train_df['target'].values))
  valid_data = tf.data.Dataset.from_tensor_slices((valid_df['question_text'].values,valid_df['target'].values))
  for text,label in train_data.take(1):
    print(text)
    print(label)

"""## Task 5: Download a Pre-trained BERT Model from TensorFlow Hub"""

"""
Each line of the dataset is composed of the review text and its label
- Data preprocessing consists of transforming text to BERT input features:
input_word_ids, input_mask, segment_ids
- In the process, tokenizing the text is done with the provided BERT model tokenizer
"""

label_list = [0,1]# Label categories
max_seq_length = 128 # maximum length of (token) input sequences
train_batch_size = 32

# Get BERT layer and tokenizer:
# More details here: https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/2

bert_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/2" ,trainable = True)

vocab_file = bert_layer.resolved_object.vocab_file.asset_path.numpy()
do_lower_case = bert_layer.resolved_object.do_lower_case.numpy()
tokenizer = tokenization.FullTokenizer(vocab_file,do_lower_case)

tokenizer.wordpiece_tokenizer.tokenize('hi, how are you doing?')

tokenizer.convert_tokens_to_ids(tokenizer.wordpiece_tokenizer.tokenize('hi, how are you doing?'))

"""## Task 6: Tokenize and Preprocess Text for BERT

<div align="center">
    <img width="512px" src='https://drive.google.com/uc?id=1-SpKFELnEvBMBqO7h3iypo8q9uUUo96P' />
    <p style="text-align: center;color:gray">Figure 2: BERT Tokenizer</p>
</div>

We'll need to transform our data into a format BERT understands. This involves two steps. First, we create InputExamples using `classifier_data_lib`'s constructor `InputExample` provided in the BERT library.
"""

# This provides a function to convert row to input features and label

def to_feature(text, label, label_list=label_list, max_seq_length=max_seq_length, tokenizer=tokenizer):
  example = classifier_data_lib.InputExample(
                                           guid=None,
                                           text_a = text.numpy(),
                                           text_b = None,
                                           label= label.numpy())
  feature = classifier_data_lib.convert_single_example(0,example,label_list,max_seq_length,tokenizer)  

  return(feature.input_ids,feature.input_mask,feature.segment_ids,feature.label_id)

"""You want to use [`Dataset.map`](https://www.tensorflow.org/api_docs/python/tf/data/Dataset#map) to apply this function to each element of the dataset. [`Dataset.map`](https://www.tensorflow.org/api_docs/python/tf/data/Dataset#map) runs in graph mode.

- Graph tensors do not have a value.
- In graph mode you can only use TensorFlow Ops and functions.

So you can't `.map` this function directly: You need to wrap it in a [`tf.py_function`](https://www.tensorflow.org/api_docs/python/tf/py_function). The [`tf.py_function`](https://www.tensorflow.org/api_docs/python/tf/py_function) will pass regular tensors (with a value and a `.numpy()` method to access it), to the wrapped python function.

## Task 7: Wrap a Python Function into a TensorFlow op for Eager Execution
"""

def to_feature_map(text,label):
  input_ids,input_mask,segment_ids,label_id = tf.py_function(to_feature,inp=[text,label],Tout=[tf.int32,tf.int32,tf.int32,tf.int32])
  
  input_ids.set_shape([max_seq_length])
  input_mask.set_shape([max_seq_length])
  segment_ids.set_shape([max_seq_length])
  label_id.set_shape([])

  x={
      'input_word_ids':input_ids,
      'input_mask':input_mask,
      'input_type_ids':segment_ids
  }
  return(x, label_id)

"""## Task 8: Create a TensorFlow Input Pipeline with `tf.data`"""

with tf.device('/cpu:0'):
  # train
  train_data = (train_data.map(to_feature_map,
                                num_parallel_calls=tf.data.experimental.AUTOTUNE)
 .shuffle(1000)
 .batch(32,drop_remainder=True)
 .prefetch(tf.data.experimental.AUTOTUNE))


  # valid
  valid_data = (valid_data.map(to_feature_map,
                                num_parallel_calls=tf.data.experimental.AUTOTUNE) 
 .batch(32,drop_remainder=True)
 .prefetch(tf.data.experimental.AUTOTUNE))

"""The resulting `tf.data.Datasets` return `(features, labels)` pairs, as expected by [`keras.Model.fit`](https://www.tensorflow.org/api_docs/python/tf/keras/Model#fit):"""

# train data spec
train_data.element_spec

# valid data spec
valid_data.element_spec

"""## Task 9: Add a Classification Head to the BERT Layer

<div align="center">
    <img width="512px" src='https://drive.google.com/uc?id=1fnJTeJs5HUpz7nix-F9E6EZdgUflqyEu' />
    <p style="text-align: center;color:gray">Figure 3: BERT Layer</p>
</div>
"""

# Building the model
def create_model():
   input_word_ids = tf.keras.layers.Input(shape=(max_seq_length,),dtype=tf.int32,name ="input_word_ids")
   input_mask= tf.keras.layers.Input(shape=(max_seq_length,),dtype=tf.int32,name ="input_mask")
   input_type_ids = tf.keras.layers.Input(shape=(max_seq_length,),dtype=tf.int32,name ="input_type_ids")

   pooled_output,sequence_output = bert_layer([input_word_ids,input_mask,input_type_ids])

   drop = tf.keras.layers.Dropout(0.4)(pooled_output)
   output = tf.keras.layers.Dense(1,activation='sigmoid', name = "output")(drop)
   model = tf.keras.Model(
       inputs = {
           'input_word_ids':input_word_ids,
           'input_mask':input_mask,
           'input_type_ids': input_type_ids
      },
      outputs = output)
   return model

"""## Task 10: Fine-Tune BERT for Text Classification"""

model = create_model()
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=2e-5),
              loss = tf.keras.losses.BinaryCrossentropy(),
              metrics = [tf.keras.metrics.BinaryAccuracy()])
model.summary()

tf.keras.utils.plot_model(model= model,show_shapes=True,dpi=76)

# Train model
epochs = 2
history = model.fit(train_data,validation_data = valid_data,epochs=epochs,verbose=1)

"""## Task 11: Evaluate the BERT Text Classification Model"""

import matplotlib.pyplot as plt

def plot_graphs(history, metric):
  plt.plot(history.history[metric])
  plt.plot(history.history['val_'+metric], '')
  plt.xlabel("Epochs")
  plt.ylabel(metric)
  plt.legend([metric, 'val_'+metric])
  plt.show()

plot_graphs(history,'loss')

plot_graphs(history,'binary_accuracy')

sample_example= []
test_data = tf.data.Dataset.from_tensor_slices((sample_example,[0]*len(sample_example)))
test_data=(test_data.map(to_feature_map).batch(1))
preds = model.predict(test_data)
threshold = #between 0 and 1
['insincere' if preds>=threshold else sincere for pred in preds]