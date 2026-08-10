package pl.lozyska.offline.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit

class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        return when (val res = SyncEngine(applicationContext).sync()) {
            is SyncResult.Success -> Result.success(workDataOf("bearings" to res.bearingCount))
            is SyncResult.NotConfigured -> Result.success() // brak adresu serwera - nic do zrobienia, nie traktuj jako błąd
            is SyncResult.Error -> Result.retry()
            // Appka za stara - ponawianie w tle nic nie zmieni bez ręcznej aktualizacji appki.
            is SyncResult.UpdateRequired -> Result.success()
        }
    }

    companion object {
        private const val UNIQUE_NAME = "lozyska_periodic_sync"

        /** Rejestruje okresową synchronizację w tle (~co godzinę, gdy jest połączenie). Bezpieczne
         * do wywołania wielokrotnie (KEEP - nie duplikuje/nie restartuje już zaplanowanej pracy). */
        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<SyncWorker>(60, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                UNIQUE_NAME, ExistingPeriodicWorkPolicy.KEEP, request,
            )
        }
    }
}
