"""
深度学习模型模块：TextCNN, LSTM, BERT
使用PyTorch实现
"""
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# ==================== TextCNN ====================
class TextCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim=128, num_filters=64, 
                 filter_sizes=(2, 3, 4), num_classes=2, dropout=0.3):
        super(TextCNN, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, num_filters, fs) for fs in filter_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(filter_sizes), num_classes)
    
    def forward(self, x):
        x = self.embedding(x)            # (batch, seq_len, embed_dim)
        x = x.permute(0, 2, 1)           # (batch, embed_dim, seq_len)
        conv_outs = []
        for conv in self.convs:
            c = torch.relu(conv(x))       # (batch, num_filters, *)
            c = torch.max(c, dim=2)[0]    # (batch, num_filters)
            conv_outs.append(c)
        x = torch.cat(conv_outs, dim=1)
        x = self.dropout(x)
        x = self.fc(x)
        return x


# ==================== LSTM ====================
class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim=128, hidden_dim=128, 
                 num_layers=2, num_classes=2, dropout=0.3):
        super(LSTMClassifier, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers=num_layers,
                           batch_first=True, dropout=dropout, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)
    
    def forward(self, x):
        x = self.embedding(x)
        lstm_out, (h_n, _) = self.lstm(x)
        # 取最后一层双向的隐藏状态拼接
        hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)
        hidden = self.dropout(hidden)
        out = self.fc(hidden)
        return out


# ==================== 简易BERT分类器 ====================
class SimpleBERTClassifier(nn.Module):
    """基于预训练词嵌入的简化BERT风格分类器（使用Transformer Encoder）"""
    def __init__(self, vocab_size, embed_dim=128, num_heads=4, 
                 num_layers=2, num_classes=2, max_len=128, dropout=0.3):
        super(SimpleBERTClassifier, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.pos_embedding = nn.Embedding(max_len, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=num_heads, 
            dim_feedforward=256, dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(embed_dim, num_classes)
    
    def forward(self, x):
        batch_size, seq_len = x.shape
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0).expand(batch_size, -1)
        x = self.embedding(x) + self.pos_embedding(positions)
        x = self.transformer(x)
        x = x.mean(dim=1)  # 平均池化
        x = self.dropout(x)
        x = self.fc(x)
        return x


# ==================== 工具函数 ====================
def build_vocab(tokenized_texts, max_vocab=10000):
    """构建词汇表"""
    word_freq = {}
    for tokens in tokenized_texts:
        for token in tokens:
            word_freq[token] = word_freq.get(token, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    vocab = {"<PAD>": 0, "<UNK>": 1}
    for word, freq in sorted_words[:max_vocab - 2]:
        vocab[word] = len(vocab)
    
    print(f"词汇表大小: {len(vocab)}")
    return vocab


def texts_to_sequences(tokenized_texts, vocab, max_len=128):
    """将分词后的文本转换为数字序列"""
    sequences = []
    for tokens in tokenized_texts:
        seq = [vocab.get(t, vocab["<UNK>"]) for t in tokens[:max_len]]
        # 填充到固定长度
        seq = seq + [0] * (max_len - len(seq))
        sequences.append(seq)
    return np.array(sequences)


def train_dl_model(model, X_train, y_train, X_val, y_val, 
                   epochs=10, batch_size=64, lr=0.001, device="cpu"):
    """
    训练深度学习模型
    
    Returns:
        model, train_time, train_losses
    """
    model = model.to(device)
    
    train_dataset = TensorDataset(
        torch.LongTensor(X_train), torch.LongTensor(y_train)
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    train_losses = []
    start_time = time.time()
    
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        avg_loss = epoch_loss / len(train_loader)
        train_losses.append(avg_loss)
        
        if (epoch + 1) % 2 == 0:
            print(f"  Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
    
    train_time = time.time() - start_time
    return model, train_time, train_losses


def predict_dl_model(model, X_test, batch_size=64, device="cpu"):
    """
    使用深度学习模型进行预测
    
    Returns:
        y_pred, y_prob, predict_time
    """
    model = model.to(device)
    model.eval()
    
    test_dataset = TensorDataset(torch.LongTensor(X_test))
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    all_probs = []
    start_time = time.time()
    
    with torch.no_grad():
        for (batch_X,) in test_loader:
            batch_X = batch_X.to(device)
            outputs = model(batch_X)
            probs = torch.softmax(outputs, dim=1)
            all_probs.append(probs.cpu().numpy())
    
    predict_time = time.time() - start_time
    all_probs = np.concatenate(all_probs, axis=0)
    y_pred = np.argmax(all_probs, axis=1)
    y_prob = all_probs[:, 1]
    
    return y_pred, y_prob, predict_time


def train_and_evaluate_all_dl(X_train_seq, y_train, X_test_seq, y_test, 
                               vocab_size, max_len=128, epochs=10, device="cpu"):
    """
    训练和评估所有深度学习模型
    
    Returns:
        dict: {model_name: {model, y_pred, y_prob, train_time, predict_time, losses}}
    """
    models_config = {
        "TextCNN": TextCNN(vocab_size=vocab_size, embed_dim=128, 
                          num_filters=64, num_classes=2),
        "BiLSTM": LSTMClassifier(vocab_size=vocab_size, embed_dim=128,
                                  hidden_dim=128, num_classes=2),
        "Transformer": SimpleBERTClassifier(vocab_size=vocab_size, embed_dim=128,
                                            num_heads=4, num_classes=2, max_len=max_len),
    }
    
    results = {}
    for name, model in models_config.items():
        print(f"\n正在训练 {name}...")
        trained_model, train_time, losses = train_dl_model(
            model, X_train_seq, y_train, X_test_seq, y_test,
            epochs=epochs, device=device
        )
        y_pred, y_prob, predict_time = predict_dl_model(
            trained_model, X_test_seq, device=device
        )
        
        results[name] = {
            "model": trained_model,
            "y_pred": y_pred,
            "y_prob": y_prob,
            "train_time": round(train_time, 3),
            "predict_time": round(predict_time, 3),
            "losses": losses,
        }
        print(f"  训练时间: {train_time:.3f}s, 预测时间: {predict_time:.3f}s")
    
    return results
