# 备选的review paper：

**Vajjala, S., & Meurers, D. (2014). Readability assessment for text simplification: From analysing documents to
identifying sentential simplifications. ITL-International Journal of Applied Linguistics, 165(2), 194-222.**

Questions:

~~1. Is the translation (Gemini) necessary?~~ using selection now
~~2. Is it necessary to scratch the subtitles or just use the single current one?~~ scrabe a few for experiments
~~3. Is gap-filling enough? How about flash card?~~ enough for the thesis
~~4. Evalution: simulation.~~ experiment with questionnaire

## 12月第二次会议：

~~1. 用中文字幕里的单词~~

~~2. 先刮取一部分，然后允许用户告知哪些需要下载~~
~~3. 用multiple gap filling，也就是找到多个包含这个词的句子，然后不出现中文~~
~~4. 用真人实验，要设计问卷 （找人？xiaobin？）~~
~~5. 已经给dennis写信了，讨论evaluation的事情~~

~~6. 新的一个view：收集所有的用户按space找到的词，然后允许用户mark已经学会的部分

7. 1月31日早上9点，online答辩
8. 下周要完成论文注册~~

## meeting 2024.01.09 Thursday

1. 用open class
2. 对于embedding的处理：无论用什么，说清楚为什么用这个，并且要出于科学研究的考量，比如我们认为contextualized embeddings have
   这样那样的必要性
3. word alignment：不需要做全word alignment，只需要在极少数词中间，进行选择，可以考虑back translation. 总之这是一个selection
   problem，用大语言模型翻译会找到同义词因此不考虑。
4. 对于用户按空格键，这些词降低权重0.15，相当于半个练习。科学研究不一定要马上找到最优解，而是摆出思考的过程，并给出选择的（基于科学的）理由。
5. 用frequency，only keep the least frequent(in the language) for 用户按下的空格键时显示的line, or give user options: all
   interesting ones, or only least frequent。考虑老师给的2个库。https://osf.io/zq49t/
   https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus
6.

去除一些特殊的大家很熟悉但是出现频率不高的词，比如爸爸妈妈，研究老师给的一个库。https://link.springer.com/article/10.3758/s13428-018-1077-9
（prevalence
norms）

7. 用cefr
   ~~
   level，去除a1、a2、b1级别的词，鉴于对实验对象的了解。https://github.com/openlanguageprofiles/olp-en-cefrj?tab=readme-ov-file~~
8. 其他：
    - least frequent 平时见不到，但是incidental vocabulary learning需要多次暴露在词汇前，因此选出来，通过更改mastery
      score来增加进入练习的概率。
    - 我们针对的不是too difficult text，而是大概3% - 5% 词汇not known的文本。
    - 如果提到性能，不要只描述它的能力，而是要写前因后果，比如前人研究如何，我做了什么，是为什么做了这些改变（what and
      why），比如速度，比如多用户同时运行。写论文的时候要展现思考过程，consideration is the part of the documentation，
      science is not by result。
    - explict testing ？
    - 有些词一旦出现过，很可能再次反复出现 什么什么birth

## meeting 2024.01.15 Wednesday

好的消息：

1. 一个想法：提前下载预备20个左右的视频和字幕资料。
   ~~2. word alignment： 用bert，也是在语义上捕捉。因为node少，所以pre- computing可行。~~
3. 对于embedding的处理: 用contextualized embeddings，用multilingual bert，因为我们的目标是多语言的，这个模型支持多种语言，因此可以更好地捕捉语义上的细微变化。
4. 我发现用cefr level和单词长度（英语，长度1和长度2），以及pos，可以filter不少的词汇。
5. 关于练习：
   一是，发现即使4个视频就可以有一些node出现2-3个例句，这是一个好现象。
   二是，因为希望增加这个app的普适性，适应多种语言，因此，考虑在用户完成练习、展示正确答案的时候，在空白划线处展示原始词汇（英语的话带有屈折），而在选项中只提供原型。
   三是，考虑在用户完成练习后，展示一个word cloud，展示用户已经学会的词汇，这样可以让用户更好地了解自己的进步。
6. 提问：文献综述的logic

advance learners : sophiscate , lack of difficult words,
don't want to wait 30 years to get another exposure, systematically repeat in short time. target-driven.

conceptually make use the foundation we have.
incidental vocabulary learning works but limited
combine it with the explicit part. It's advanced.

收获：

1. **根据所有试图解决的问题来组织related work的逻辑。比如，我try to character words, therefore, we have reviewed those
   approaches,...
2. background也以此为准。**

3. try to set a server up。
4. 关于练习：提到choose by meaning和choose by form的区别，提到我们的练习再次adopt了word
   family的概念，不只是prefix和sufix，也包括类似unhappy这种派生。这也再次呼应了incidental vocabulary
   learning的需求，也就是理解。但是我们展示词汇本身的形态，也是一种lemma+meaning+form。只不过focus在meaning。
5. 下次会议：1月20日4.30pm. 最好show paper和完全的frontend。

2024年1月20日会议：
问题：

1. 视频数量过少（比如1个）的时候有几率无法生成练习或者质量很差。（需要再次检查只有一个视频的情况。）
2. distractor无法指定pos。这是因为我们考察lemma在多个context里的情况。但结果是在视频数量少的时候，因此distractor在早期出现质量很差的情况。
3. 计算和生成练习需要的时间略有点长。是否不利用最近一次word list的结果？
4. 除了word list里给出translation，以及word embedding里使用了multi-language trained bert，这个bilingual的意义在哪里？

Summary:

1. 用shift key代替spacebar，并且按动的时候，浮现的提示指出所选词汇。
2. 在视频窗口右边空白处，列出所选词汇，可以上下scroll，对用户transparent，用户不满意的话，点击该词汇，出现line，用户重新点击一个词汇，取代系统选出的词汇；有可能的话，right
   click，选取新词但是不取代之前的词。并且提供一个check box或者垃圾桶图标，允许用户删除词汇。
3. 把word list页面的mark as known改成checkbox或者垃圾桶图标。未来：展示相应的视频clip。
4. 对于graph展示，加入search部分，允许搜索node。高亮node和连接的node。
5. 练习页面：改成一次展示一道题，如果选错了，最好把错误选项标成红色，不行的话，就在选项框前面加红叉。如果选错了，让用户继续选择，直到选到正确选项为止。每次选错都reduce
   benefit，如果错误3次以上才选对，不增加任何mastery score。并且从一次选对到后续再选对，增加的mastery score递减。递减数字还要考虑。
6. 练习页面：加入skip按钮，表明这个词完全不会。mastery score降低。
7. 练习页面：如果一次只预先出一道题，那么期待等待时间能够减少。
8. 关于bilingual的用途: it's in particular usage: trigger stage, better understanding of word sense and
   syntactic， disambiguiate word sense and also syntactic form, the realization of
   the user for this word will be different. Not only shorten the time of learning the word, but also deeper and broad
   the understanding of the word. (
   这两点很重要。不只是帮助学习者学习新词汇，更帮助学习者能够学到这个词汇的不同屈折派生等表达和用处。). Normally, the
   learner has
   limited access to
   meaning, but with the bilingual, the learner can have a better understanding of the word: once you see it, you
   have one exporsure to the meaning and the form. The subtitle in native language, provice access to the
   particular meaning。 ensure that incidental exposure to the material - meaning.
9. 用word-family-root来代替lemma的说法。因为有可能lemma是跟pos绑定的概念，lemma might be pos specific?，要查文献。目前的练习允许get
   different pos across different context。


1. intro: what motivate more: there are video resources, incidental VL takes too long (6-8)->need a mixure, enter the
   domain by .., allow easy identification, support the organization, turn incident to, support multi\native language.

oral form and the meaning.

full reasoning.
make it easy computer support

2.3 start with : short paragraph about when turning incident to explict, one can easily identify words, but words need
context and semantic disamgui.., fortuately, there is a NLP tech
organzing semantic material into space.

word embedding: vectors

word families: should we do it with all words? No. only with families of words.

(To connect differnt techniques)

Organizing the lexical space (big title)

2.4 Expert model/ model the domain of learning

Expertise the learner models
stepwise, competing knowledge and competences. we can use the vocabulary graph. gain lexical representation... step by
step to build the learner model on the domain model.

2.5 learner motivation (compound)

chapter 3

3.2 first
then 3.1

3.3 game investigation

chat 4: Our approach:  (strongly imply implicit learning) from implicit exposure to ...learning
= FIEL: from implicit vocabulary learning to explicit vocabulary learning
FIEEL

sub-titles' style: what I am trying to do

which version of Chinese should I use?

4.1.3 explain the 翻译人员/。。。

figure 4.1

关于这些cet考试的东西，可以移到前面的bilingual embeddings:
in the background, we talked about word embeddings/ we introduced

refer to the background

https://link.springer.com/article/10.1186/s12859-015-0606-0 提到的方法lp，也是用vector，可以作为distributioanl
semantics在语言学习之外应用的例子

=========================2月会议=========================

1. intro: what motivate more: there are video resources, incidental VL takes too long (6-8)->need a mixure, enter the
   domain by .., allow easy identification, support the organization, turn incident to, support multi\native language.

oral form and the meaning.

full reasoning.
make it easy computer support

2.3 start with : short paragraph about when turning incident to explict, one can easily identify words, but words need
context and semantic disamgui.., fortuately, there is a NLP tech
organzing semantic material into space.

word embedding: vectors

word families: should we do it with all words? No. only with families of words.

(To connect differnt techniques)

Organizing the lexical space (big title)

2.4 Expert model/ model the domain of learning

Expertise the learner models
stepwise, competing knowledge and competences. we can use the vocabulary graph. gain lexical representation... step by
step to build the learner model on the domain model.

2.5 learner motivation (compound)

chapter 3

3.2 first
then 3.1

3.3 game investigation

chat 4: Our approach:  (strongly imply implicit learning) from implicit exposure to ...learning
= FIEL: from implicit vocabulary learning to explicit vocabulary learning
FIEEL

sub-titles' style: what I am trying to do

which version of Chinese should I use?

~~4.1.3 explain the 翻译人员/。。。~~

figure 4.1

关于这些cet考试的东西，可以移到前面的bilingual embeddings:
in the background, we talked about word embeddings/ we introduced

refer to the background
























