import android.app.Application

class BankingApp : Application()

// app/src/main/java/com/example/banking/model/Account.kt
package com.example.banking.model

import java.math.BigDecimal
import java.time.LocalDateTime
import java.util.UUID

data class Account(
    val id: String,
    val ownerName: String,
    val currency: String,
    val balance: BigDecimal
)

enum class TransactionType {
    DEPOSIT,
    WITHDRAWAL
}

data class Transaction(
    val id: String = UUID.randomUUID().toString(),
    val accountId: String,
    val type: TransactionType,
    val amount: BigDecimal,
    val timestamp: LocalDateTime,
    val description: String? = null,
    val resultingBalance: BigDecimal
)

// app/src/main/java/com/example/banking/data/InMemoryAccountRepository.kt
package com.example.banking.data

import com.example.banking.model.Account
import com.example.banking.model.Transaction
import com.example.banking.model.TransactionType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import java.math.BigDecimal
import java.time.LocalDateTime
import java.util.UUID

class InMemoryAccountRepository {

    private val accountState: MutableStateFlow<Account>
    private val transactionsState: MutableStateFlow<List<Transaction>>

    init {
        val initialAccount = Account(
            id = UUID.randomUUID().toString(),
            ownerName = "Demo User",
            currency = "USD",
            balance = BigDecimal("1250.00")
        )
        accountState = MutableStateFlow(initialAccount)
        transactionsState = MutableStateFlow(emptyList())
    }

    fun observeAccount(): Flow<Account> = accountState

    fun observeTransactions(): Flow<List<Transaction>> = transactionsState

    @Synchronized
    fun processTransaction(
        type: TransactionType,
        amount: BigDecimal,
        description: String?
    ): Result<Transaction> {
        if (amount <= BigDecimal.ZERO) {
            return Result.failure(IllegalArgumentException("Amount must be greater than zero"))
        }

        val currentAccount = accountState.value
        val newBalance = when (type) {
            TransactionType.DEPOSIT -> currentAccount.balance + amount
            TransactionType.WITHDRAWAL -> {
                if (currentAccount.balance < amount) {
                    return Result.failure(IllegalStateException("Insufficient funds"))
                }
                currentAccount.balance - amount
            }
        }

        val tx = Transaction(
            accountId = currentAccount.id,
            type = type,
            amount = amount,
            timestamp = LocalDateTime.now(),
            description = description?.take(80),
            resultingBalance = newBalance
        )

        accountState.value = currentAccount.copy(balance = newBalance)
        transactionsState.update { listOf(tx) + it.take(49) }

        return Result.success(tx)
    }
}

// app/src/main/java/com/example/banking/ui/BankingViewModel.kt
package com.example.banking.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.banking.data.InMemoryAccountRepository
import com.example.banking.model.Account
import com.example.banking.model.Transaction
import com.example.banking.model.TransactionType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.math.BigDecimal

data class BankingUiState(
    val account: Account? = null,
    val transactions: List<Transaction> = emptyList(),
    val isProcessing: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class BankingViewModel(
    private val repository: InMemoryAccountRepository = InMemoryAccountRepository()
) : ViewModel() {

    private val isProcessingState = MutableStateFlow(false)
    private val errorState = MutableStateFlow<String?>(null)
    private val successState = MutableStateFlow<String?>(null)

    val uiState: StateFlow<BankingUiState> = combine(
        repository.observeAccount(),
        repository.observeTransactions(),
        isProcessingState,
        errorState,
        successState
    ) { account, transactions, isProcessing, error, success ->
        BankingUiState(
            account = account,
            transactions = transactions,
            isProcessing = isProcessing,
            errorMessage = error,
            successMessage = success
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = BankingUiState()
    )

    fun clearMessages() {
        errorState.value = null
        successState.value = null
    }

    fun processDeposit(amountRaw: String, description: String?) {
        processTransactionInternal(TransactionType.DEPOSIT, amountRaw, description)
    }

    fun processWithdrawal(amountRaw: String, description: String?) {
        processTransactionInternal(TransactionType.WITHDRAWAL, amountRaw, description)
    }

    private fun processTransactionInternal(
        type: TransactionType,
        amountRaw: String,
        description: String?
    ) {
        viewModelScope.launch {
            clearMessages()
            val normalized = amountRaw.trim().replace(",", "")
            val amount = normalized.toBigDecimalOrNull()
            if (amount == null) {
                errorState.value = "Invalid amount format"
                return@launch
            }
            if (amount.scale() > 2) {
                errorState.value = "Use at most two decimal places"
                return@launch
            }

            isProcessingState.value = true
            val result = repository.processTransaction(type, amount, description)
            isProcessingState.value = false

            result
                .onSuccess {
                    successState.value = when (type) {
                        TransactionType.DEPOSIT -> "Deposit successful"
                        TransactionType.WITHDRAWAL -> "Withdrawal successful"
                    }
                }
                .onFailure { throwable ->
                    errorState.value = throwable.message ?: "Transaction failed"
                }
        }
    }
}

// app/src/main/java/com/example/banking/ui/theme/Theme.kt
package com.example.banking.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF006E5B),
    onPrimary = Color.White,
    background = Color(0xFFFAFAFA),
    onBackground = Color(0xFF1C1B1F),
    surface = Color.White,
    onSurface = Color(0xFF1C1B1F),
    error = Color(0xFFB3261E)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF4FD8C6),
    onPrimary = Color(0xFF00382F),
    background = Color(0xFF121212),
    onBackground = Color(0xFFE5E1E6),
    surface = Color(0xFF1E1E1E),
    onSurface = Color(0xFFE5E1E6),
    error = Color(0xFFF2B8B5)
)

@Composable
fun BankingTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colors = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colors,
        typography = Typography,
        content = content
    )
}

// app/src/main/java/com/example/banking/ui/theme/Type.kt
package com.example.banking.ui.theme

import androidx.compose.material3.Typography

val Typography = Typography()

// app/src/main/java/com/example/banking/MainActivity.kt
package com.example.banking

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberTopAppBarState
import androidx.compose.material3.rememberTopAppBarScrollBehavior
import androidx.compose.material3.icons.Icons
import androidx.compose.material3.icons.filled.ArrowDownward
import androidx.compose.material3.icons.filled.ArrowUpward
import androidx.compose.material3.icons.filled.Info
import androidx.compose.material3.icons.filled.Refresh
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.BaselineShift
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.banking.model.Transaction
import com.example.banking.model.TransactionType
import com.example.banking.ui.BankingUiState
import com.example.banking.ui.BankingViewModel
import com.example.banking.ui.theme.BankingTheme
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.format.DateTimeFormatter

class MainActivity : ComponentActivity() {

    private val viewModel: BankingViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BankingTheme {
                BankingAppRoot(viewModel = viewModel)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BankingAppRoot(viewModel: BankingViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(uiState.errorMessage, uiState.successMessage) {
        uiState.errorMessage?.let {
            scope.launch {
                snackbarHostState.showSnackbar(it)
                viewModel.clearMessages()
            }
        }
        uiState.successMessage?.let {
            scope.launch {
                snackbarHostState.showSnackbar(it)
                viewModel.clearMessages()
            }
        }
    }

    val scrollBehavior = rememberTopAppBarScrollBehavior(rememberTopAppBarState())

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(
                WindowInsets.safeDrawing.only(
                    WindowInsets.statusBars + WindowInsets.navigationBars
                )
            ),
        topBar = {
            TopAppBar(
                title = { Text(text = "Secure Bank (Demo)") },
                actions = {
                    IconButton(onClick = { /* Optionally refresh or future actions */ }) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Refresh"
                        )
                    }
                },
                scrollBehavior = scrollBehavior
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            color = MaterialTheme.colorScheme.background
        ) {
            if (uiState.account == null) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "Loading account…")
                }
            } else {
                BankingHomeContent(
                    uiState = uiState,
                    onDeposit = { amount, description ->
                        viewModel.processDeposit(amount, description)
                    },
                    onWithdraw = { amount, description ->
                        viewModel.processWithdrawal(amount, description)
                    }
                )
            }
        }
    }
}

@Composable
fun BankingHomeContent(
    uiState: BankingUiState,
    onDeposit: (String, String?) -> Unit,
    onWithdraw: (String, String?) -> Unit
) {
    val focusManager = LocalFocusManager.current
    var amountInput by remember { mutableStateOf("") }
    var descriptionInput by remember { mutableStateOf("") }
    var showInfoDialog by remember { mutableStateOf(false) }

    if (showInfoDialog) {
        InfoDialog(onDismiss = { showInfoDialog = false })
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = uiState.account?.ownerName.orEmpty(),
                style = MaterialTheme.typography.titleMedium
            )
            IconButton(onClick = { showInfoDialog = true }) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = "Account info"
                )
            }
        }

        AccountBalanceCard(
            currency = uiState.account?.currency.orEmpty(),
            balance = uiState.account?.balance ?: BigDecimal.ZERO
        )

        TransactionFormCard(
            amountInput = amountInput,
            onAmountChange = { amountInput = it },
            descriptionInput = descriptionInput,
            onDescriptionChange = { descriptionInput = it },
            isProcessing = uiState.isProcessing,
            onDepositClick = {
                focusManager.clearFocus()
                onDeposit(amountInput, descriptionInput.ifBlank { null })
            },
            onWithdrawClick = {
                focusManager.clearFocus()
                onWithdraw(amountInput, descriptionInput.ifBlank { null })
            }
        )

        Text(
            text = "Recent transactions",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(top = 8.dp, bottom = 4.dp)
        )

        Divider()

        if (uiState.transactions.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "No transactions yet",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentPadding = PaddingValues(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(uiState.transactions) { tx ->
                    TransactionRow(transaction = tx)
                }
            }
        }
    }
}

@Composable
fun AccountBalanceCard(
    currency: String,
    balance: BigDecimal
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.primary
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Current balance",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
            )
            Text(
                text = formatCurrency(balance, currency),
                style = MaterialTheme.typography.headlineMedium.copy(
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.SemiBold
                )
            )
        }
    }
}

@Composable
fun TransactionFormCard(
    amountInput: String,
    onAmountChange: (String) -> Unit,
    descriptionInput: String,
    onDescriptionChange: (String) -> Unit,
    isProcessing: Boolean,
    onDepositClick: () -> Unit,
    onWithdrawClick: () -> Unit
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "New transaction",
                style = MaterialTheme.typography.titleMedium
            )

            OutlinedTextField(
                value = amountInput,
                onValueChange = { newValue ->
                    if (newValue.length <= 12) {
                        onAmountChange(newValue.filter { it.isDigit() || it == '.' || it == ',' })
                    }
                },
                label = { Text("Amount") },
                placeholder = { Text("e.g. 50.00") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                textStyle = LocalTextStyle.current.copy(fontSize = 16.sp)
            )

            OutlinedTextField(
                value = descriptionInput,
                onValueChange = { if (it.length <= 80) onDescriptionChange(it) },
                label = { Text("Description (optional)") },
                placeholder = { Text("Short note for this transaction") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                textStyle = LocalTextStyle.current.copy(fontSize = 14.sp)
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = onDepositClick,
                    enabled = !isProcessing
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowDownward,
                        contentDescription = "Deposit"
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = if (isProcessing) "Processing…" else "Deposit")
                }
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = onWithdrawClick,
                    enabled = !isProcessing
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowUpward,
                        contentDescription = "Withdraw"
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = if (isProcessing) "Processing…" else "Withdraw")
                }
            }
        }
    }
}

@Composable
fun TransactionRow(transaction: Transaction) {
    val isDeposit = transaction.type == TransactionType.DEPOSIT
    val iconBackground = if (isDeposit) Color(0xFF1B5E20) else Color(0xFFB71C1C)
    val iconTint = Color.White
    val amountColor = if (isDeposit) Color(0xFF2E7D32) else Color(0xFFC62828)

    val timestampFormatter = remember {
        DateTimeFormatter.ofPattern("MMM d • HH:mm")
    }

    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(
                modifier = Modifier
                    .height(40.dp)
                    .clip(CircleShape)
                    .background(iconBackground),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = if (isDeposit) Icons.Default.ArrowDownward else Icons.Default.ArrowUpward,
                    contentDescription = null,
                    tint = iconTint
                )
            }

            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                Text(
                    text = if (isDeposit) "Deposit" else "Withdrawal",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        fontWeight = FontWeight.SemiBold
                    )
                )
                AnimatedVisibility(
                    visible = !transaction.description.isNullOrBlank(),
                    enter = fadeIn(),
                    exit = fadeOut()
                ) {
                    Text(
                        text = transaction.description.orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }
                Text(
                    text = transaction.timestamp.format(timestampFormatter),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }

            Column(
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                Text(
                    text = (if (isDeposit) "+" else "-") +
                            formatCurrencyAmount(transaction.amount),
                    style = MaterialTheme.typography.bodyMedium.copy(
                        fontWeight = FontWeight.SemiBold,
                        color = amountColor
                    )
                )
                Text(
                    text = "Bal: " + formatCurrencyAmount(transaction.resultingBalance),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
fun InfoDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(text = "Demo account")
        },
        text = {
            Text(
                text = "This is a local-only demo of secure transaction handling. " +
                        "Amounts and balances are simulated on your device and are not connected to real bank accounts."
            )
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text(text = "OK")
            }
        }
    )
}

private fun formatCurrency(amount: BigDecimal, currency: String): String {
    val code = if (currency.isBlank()) "USD" else currency.uppercase()
    return "$code ${formatCurrencyAmount(amount)}"
}

private fun formatCurrencyAmount(amount: BigDecimal): String {
    val scaled = amount.setScale(2, BigDecimal.ROUND_HALF_EVEN)
    val text = scaled.toPlainString()
    val parts = text.split(".")
    val integerPart = parts[0].reversed().chunked(3).joinToString(",").reversed()
    val decimalPart = parts.getOrNull(1) ?: "00"
    return "$integerPart.$decimalPart"
}