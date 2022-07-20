<template>
    <div>
        <v-progress-linear
            color="primary accent-4"
            indeterminate
            rounded
            height="4"
            :active="loading"
        ></v-progress-linear>
        <div>
            <b>{{ collectionid }} Caches</b>
        </div>
        <v-card v-if="collectioncaches.length > 0">
            <v-list-item v-for="item in collectioncaches" :key=item.cache_name two-line>
                <v-list-item-content>
                    <v-list-item-title>{{ item.cache_name }}</v-list-item-title>
                    <v-list-item-subtitle>
                        <div>
                            priority: {{ item.priority }}
                        </div>
                        <v-btn color="warning" @click="deleteCache(item.cache_name)">
                            Delete
                    </v-btn>
                    </v-list-item-subtitle>
                </v-list-item-content>
            </v-list-item>
        </v-card>
        <div v-else>
            There is no collection with ID {{ collectionid }} in our database
        </div>
        <br />

        <v-dialog v-model="dialog" width="500">
            <template v-slot:activator="{ on, attrs }">
                <v-btn color="green" dark v-bind="attrs" v-on="on">
                    Add/edit cache
                </v-btn>
            </template>

            <v-card>
                <v-card-title color="#49075e">
                    Add or edit cache
                </v-card-title>

                <v-card-text>
                    <v-row>
                        <v-col>
                            <v-select
                                :items="caches"
                                v-model="selectedCache"
                                outlined
                                label="Cache"
                                item-text="name"
                                item-value="name"
                                @change="selectChanged"
                            ></v-select>
                        </v-col>

                        <v-col>
                            <v-text-field
                                v-model="priority"
                                append-icon="mdi-priority-high"
                                label="Cache priority"
                                single-line
                                hide-details
                                :rules="numberRules"
                            ></v-text-field>
                        </v-col>
                    </v-row>
                </v-card-text>

                <v-divider></v-divider>

                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" text @click="addEditCache">
                        Submit
                    </v-btn>
                    <v-spacer></v-spacer>
                </v-card-actions>
            </v-card>
        </v-dialog>

    </div>
</template>

<script>
    // import Vue from 'vue'
    import CollectionAPI from "@/api/CollectionAPI"

    export default {
        name: 'Collection',

        data() {
            return {
                loading: false,
                dialog: false,
                selectedCache: "",
                priority: 0,
                collectionid: "",
                collectioncaches: [],
                caches: [],
                numberRules: [
                    value => value && value >= 0 || 'Must be 0 or a positive number'
                ],
            }
        },
        methods: {
            async addEditCache(){
                this.dialog = false
                await CollectionAPI.createCollectionCache(this.collectionid, this.selectedCache, this.priority)
                this.collectioncaches = await CollectionAPI.getCollectionCaches(this.collectionid)
            },
            selectChanged(){
                this.caches.forEach(cache => {
                    if(cache.cache_name === this.selectedCache){
                        this.priority = cache.priority
                    }
                });
            },
            async deleteCache(cachename){
                await CollectionAPI.deleteCollectionCache(this.collectionid, cachename)
                this.collectioncaches = await CollectionAPI.getCollectionCaches(this.collectionid)
            }
        },
        mounted: async function() {
            this.loading = true
            this.collectionid = this.$route.query.id
            this.caches = await CollectionAPI.getCaches()
            console.log(this.caches)
            this.collectioncaches = await CollectionAPI.getCollectionCaches(this.collectionid)
            console.log(this.collectioncaches)
            this.loading = false
        },

    }
</script>