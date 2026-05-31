package com.socialshield

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.*
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.google.firebase.auth.FirebaseAuth
import com.socialshield.domain.models.ScanType
import com.socialshield.ui.screens.*
import com.socialshield.ui.theme.*
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SocialShieldTheme {
                SocialShieldApp(isLoggedIn = auth.currentUser != null)
            }
        }
    }
}

object Routes {
    const val SPLASH = "splash"
    const val ONBOARDING = "onboarding"
    const val AUTH = "auth"
    const val HOME = "home"
    const val SCAN = "scan/{scanType}"
    const val PROCESSING = "processing"
    const val RESULT = "result/{scanId}"
    const val HISTORY = "history"
    const val FRAUD_MAP = "fraud_map"
    const val SETTINGS = "settings"

    fun scan(type: ScanType) = "scan/${type.name}"
    fun result(scanId: String) = "result/$scanId"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SocialShieldApp(isLoggedIn: Boolean) {
    val navController = rememberNavController()
    val currentRoute by navController.currentBackStackEntryAsState()
    val showBottomBar = currentRoute?.destination?.route in listOf(
        Routes.HOME, Routes.HISTORY, Routes.FRAUD_MAP, Routes.SETTINGS
    )

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            if (showBottomBar) {
                ShieldBottomBar(
                    currentRoute = currentRoute?.destination?.route,
                    onNavigate = { route ->
                        navController.navigate(route) {
                            popUpTo(Routes.HOME) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.SPLASH,
            modifier = Modifier.padding(padding),
            enterTransition = { slideInHorizontally(tween(300)) { it } + fadeIn(tween(300)) },
            exitTransition = { slideOutHorizontally(tween(300)) { -it } + fadeOut(tween(300)) },
            popEnterTransition = { slideInHorizontally(tween(300)) { -it } + fadeIn(tween(300)) },
            popExitTransition = { slideOutHorizontally(tween(300)) { it } + fadeOut(tween(300)) }
        ) {
            composable(Routes.SPLASH) {
                SplashScreen(
                    onNavigateNext = {
                        val destination = if (isLoggedIn) Routes.HOME else Routes.ONBOARDING
                        navController.navigate(destination) {
                            popUpTo(Routes.SPLASH) { inclusive = true }
                        }
                    }
                )
            }

            composable(Routes.ONBOARDING) {
                OnboardingScreen(
                    onGetStarted = {
                        navController.navigate(Routes.AUTH) {
                            popUpTo(Routes.ONBOARDING) { inclusive = true }
                        }
                    }
                )
            }

            composable(Routes.AUTH) {
                AuthScreen(
                    onAuthSuccess = {
                        navController.navigate(Routes.HOME) {
                            popUpTo(Routes.AUTH) { inclusive = true }
                        }
                    }
                )
            }

            composable(Routes.HOME) {
                HomeScreen(
                    onScanClick = { type -> navController.navigate(Routes.scan(type)) },
                    onHistoryClick = { navController.navigate(Routes.HISTORY) },
                    onFraudMapClick = { navController.navigate(Routes.FRAUD_MAP) }
                )
            }

            composable(
                Routes.SCAN,
                arguments = listOf(navArgument("scanType") { type = NavType.StringType })
            ) { entry ->
                val scanTypeName = entry.arguments?.getString("scanType") ?: ScanType.IMAGE.name
                val scanType = ScanType.valueOf(scanTypeName)
                ScanScreen(
                    scanType = scanType,
                    onBack = { navController.popBackStack() },
                    onResultReady = { scanId ->
                        navController.navigate(Routes.result(scanId)) {
                            popUpTo(Routes.HOME) { inclusive = false }
                        }
                    }
                )
            }

            composable(
                Routes.RESULT,
                arguments = listOf(navArgument("scanId") { type = NavType.StringType })
            ) { entry ->
                val scanId = entry.arguments?.getString("scanId") ?: ""
                ResultScreen(
                    scanId = scanId,
                    onBack = { navController.popBackStack() },
                    onScanAgain = {
                        navController.navigate(Routes.HOME) {
                            popUpTo(Routes.HOME) { inclusive = false }
                        }
                    }
                )
            }

            composable(Routes.HISTORY) {
                HistoryScreen(
                    onBack = { navController.popBackStack() },
                    onScanDetail = { scanId -> navController.navigate(Routes.result(scanId)) }
                )
            }

            composable(Routes.FRAUD_MAP) {
                FraudMapScreen(onBack = { navController.popBackStack() })
            }

            composable(Routes.SETTINGS) {
                SettingsScreen(
                    onBack = { navController.popBackStack() },
                    onSignOut = {
                        navController.navigate(Routes.AUTH) {
                            popUpTo(0) { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}

@Composable
fun ShieldBottomBar(currentRoute: String?, onNavigate: (String) -> Unit) {
    val items = listOf(
        Triple(Routes.HOME, Icons.Default.Home, "Home"),
        Triple(Routes.HISTORY, Icons.Default.History, "History"),
        Triple(Routes.FRAUD_MAP, Icons.Default.Public, "Map"),
        Triple(Routes.SETTINGS, Icons.Default.Settings, "Settings")
    )

    NavigationBar(
        containerColor = DarkSurface,
        tonalElevation = 0.dp
    ) {
        items.forEach { (route, icon, label) ->
            val selected = currentRoute == route
            NavigationBarItem(
                icon = { Icon(icon, contentDescription = label, modifier = Modifier.padding(0.dp)) },
                label = { Text(label, fontSize = 11.sp) },
                selected = selected,
                onClick = { onNavigate(route) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = NeonBlue,
                    selectedTextColor = NeonBlue,
                    unselectedIconColor = Color.White.copy(0.4f),
                    unselectedTextColor = Color.White.copy(0.4f),
                    indicatorColor = NeonBlue.copy(0.15f)
                )
            )
        }
    }
}
