<template>
    <div>
        <v-progress-linear
            color="primary accent-4"
            indeterminate
            rounded
            height="4"
            :active="loading"
        ></v-progress-linear>

    </div>
</template>

<script>
    // import Vue from 'vue'
    // import ProjectAPI from "@/api/ProjectAPI"

    export default {
        name: 'Collections',

        data() {
            return {
                loading: false,
                collectionid: 0,
                collection: {}
            }
        },
        methods: {

        },
        mounted: async function() {
            this.loading = true
            this.collectionid = this.$route.query.id
            this.loading = false
        },

    }
</script>