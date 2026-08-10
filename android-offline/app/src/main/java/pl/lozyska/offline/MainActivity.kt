package pl.lozyska.offline

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.material.icons.filled.Warehouse
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import pl.lozyska.offline.sync.RELEASES_URL
import pl.lozyska.offline.sync.SyncWorker

class MainActivity : ComponentActivity() {
    private val vm: OfflineViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SyncWorker.schedulePeriodic(applicationContext)
        setContent {
            LozyskaOfflineTheme {
                AppScaffold(vm)
            }
        }
    }
}

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val TABS = listOf(
    Tab("bearings", "Łożyska", Icons.Filled.List),
    Tab("shelves", "Regały", Icons.Filled.Warehouse),
    Tab("data", "Dane", Icons.Filled.Storage),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScaffold(vm: OfflineViewModel) {
    val navController = rememberNavController()
    val snackbarHostState = remember { SnackbarHostState() }
    val context = LocalContext.current

    val message by vm.message.collectAsState()
    LaunchedEffect(message) {
        message?.let {
            snackbarHostState.showSnackbar(it)
            vm.clearMessage()
        }
    }

    val updateRequired by vm.updateRequired.collectAsState()
    val updateAvailable by vm.updateAvailable.collectAsState()
    val latestServerVersion by vm.latestServerVersion.collectAsState()
    val openReleases = {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(RELEASES_URL)))
    }

    // Synchronizacja przy otwarciu appki i za każdym razem, gdy adres serwera się zmieni
    // (StateFlow z DataStore ładuje się asynchronicznie, więc kluczujemy efekt na jego
    // wartości, a nie na Unit - inaczej można by złapać jeszcze niezaładowaną wartość "").
    val serverUrl by vm.serverUrl.collectAsState()
    LaunchedEffect(serverUrl) {
        if (serverUrl.isNotBlank()) vm.syncNow()
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            val backStackEntry by navController.currentBackStackEntryAsState()
            val currentRoute = backStackEntry?.destination
            NavigationBar {
                TABS.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute?.hierarchy?.any { it.route == tab.route } == true,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        }
    ) { padding ->
        Column(Modifier.padding(padding)) {
            if (updateRequired) {
                UpdateBanner(
                    text = "Ta wersja appki jest za stara i nie może już synchronizować się z serwerem " +
                        (latestServerVersion?.let { "(serwer: $it)" } ?: "") +
                        ". Dane offline działają dalej, ale zaktualizuj appkę, żeby wznowić synchronizację.",
                    containerColor = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer,
                    onUpdateClick = openReleases,
                )
            } else if (updateAvailable) {
                UpdateBanner(
                    text = "Dostępna nowsza wersja appki" +
                        (latestServerVersion?.let { " ($it)" } ?: "") + ".",
                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                    onUpdateClick = openReleases,
                )
            }
            NavHost(
                navController = navController,
                startDestination = "bearings",
                modifier = Modifier.weight(1f),
            ) {
                composable("bearings") { BearingsScreen(vm) }
                composable("shelves") { ShelvesScreen(vm) }
                composable("data") { DataScreen(vm) }
            }
        }
    }
}

@Composable
private fun UpdateBanner(
    text: String,
    containerColor: androidx.compose.ui.graphics.Color,
    contentColor: androidx.compose.ui.graphics.Color,
    onUpdateClick: () -> Unit,
) {
    Surface(color = containerColor, contentColor = contentColor) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.SystemUpdate, contentDescription = null, modifier = Modifier.padding(end = 10.dp))
            Text(text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
            TextButton(onClick = onUpdateClick) { Text("Aktualizuj") }
        }
    }
}
